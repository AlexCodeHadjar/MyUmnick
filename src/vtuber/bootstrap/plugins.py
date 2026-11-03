"""Загрузка плагинов (Этап 12): entry points `vtuber.plugins`, включённые в `[plugins].enabled`.

Плагин — чужой код: сбой при загрузке, старте или остановке пишется в лог и не мешает приложению.
Ни один плагин не включён — нет ни поиска пакетов, ни задач, ни подписок.
"""

import asyncio
from collections.abc import AsyncIterator, Callable, Iterable, Mapping
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field
from importlib.metadata import EntryPoint, entry_points
from typing import Final

from vtuber.application.scheduler import ModelSpec, Priority, ResourceManager
from vtuber.domain import ConfigError
from vtuber.kernel import (
    Command,
    ContextTool,
    EventBus,
    LoadableModel,
    MessageStream,
    ModelHost,
    Plugin,
    PluginContext,
    PluginsConfig,
    get_logger,
)

ENTRY_POINT_GROUP: Final = "vtuber.plugins"

type Discover = Callable[[], Iterable[EntryPoint]]

_log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class PluginServices:
    """Что плагины дали ядру в `setup`: источники реплик и справку хода."""

    sources: tuple[MessageStream, ...] = ()
    contexts: tuple[ContextTool, ...] = ()
    commands: Mapping[str, Command] = field(default_factory=dict)


class ResourceModels:
    """Менеджер ресурсов для плагинов: у ядра нет к нему прямого пути (ADR-0005)."""

    def __init__(self, manager: ResourceManager) -> None:
        self._manager = manager

    def hold(
        self, name: str, vram_mb: int, model: LoadableModel
    ) -> Callable[[], AbstractAsyncContextManager[None]]:
        """Инструмент важнее фона, но диалог не вытесняет (ADR-0017)."""
        self._manager.register(ModelSpec(name, vram_mb, Priority.TOOL), model)
        return lambda: self._manager.use(name)


@dataclass(frozen=True, slots=True)
class _Started:
    plugin: Plugin
    ctx: PluginContext


def _installed() -> Iterable[EntryPoint]:
    return entry_points(group=ENTRY_POINT_GROUP)


@asynccontextmanager
async def running_plugins(
    cfg: PluginsConfig,
    bus: EventBus,
    discover: Discover = _installed,
    models: ModelHost | None = None,
) -> AsyncIterator[PluginServices]:
    """Включённые плагины работают на время контекста; остановка — в обратном порядке.

    Отдаёт то, что плагины зарегистрировали в `setup`.
    """
    if not cfg.enabled:
        yield PluginServices()
        return
    found = {point.name: point for point in discover()}
    attempts = []
    for name in cfg.enabled:
        ctx = PluginContext(name, bus, cfg.settings.get(name, {}), models)
        attempts.append(await _start(found.get(name), cfg, ctx))
    started = [one for one in attempts if one is not None]
    pumps = [asyncio.create_task(one.ctx.run()) for one in started]
    try:
        yield PluginServices(
            tuple(stream for one in started for stream in one.ctx.sources),
            tuple(provider for one in started for provider in one.ctx.contexts),
            {text: cmd for one in started for text, cmd in one.ctx.commands.items()},
        )
    finally:
        for pump in pumps:
            pump.cancel()
        await asyncio.gather(*pumps, return_exceptions=True)
        for one in reversed(started):
            await _stop(one, cfg.shutdown_timeout_s)


async def _start(
    point: EntryPoint | None, cfg: PluginsConfig, ctx: PluginContext
) -> _Started | None:
    name = ctx.name
    if point is None:
        # Не ошибка конфига: снятый пакет не должен лишать пользователя приложения.
        _log.warning("plugin.not_installed", plugin=name)
        return None
    try:
        # Импорт чужого пакета может быть долгим: цикл событий не блокируется (R-34).
        plugin = await asyncio.to_thread(_load, point)
        async with asyncio.timeout(cfg.setup_timeout_s):
            await plugin.setup(ctx)
    except Exception:  # noqa: BLE001 — R-42: граница плагина, приложение работает без него
        ctx.close()
        _log.exception("plugin.setup_failed", plugin=name)
        return None
    _log.info("plugin.started", plugin=name)
    return _Started(plugin, ctx)


def _load(point: EntryPoint) -> Plugin:
    plugin = point.load()()
    if not isinstance(plugin, Plugin):
        msg = f"Entry point {point.value} не реализует Plugin (name, setup, shutdown)"
        raise ConfigError(msg)
    if plugin.name != point.name:
        msg = f"Плагин называет себя '{plugin.name}', а entry point — '{point.name}'"
        raise ConfigError(msg)
    return plugin


async def _stop(one: _Started, timeout_s: float) -> None:
    one.ctx.close()
    try:
        async with asyncio.timeout(timeout_s):
            await one.plugin.shutdown()
    except Exception:  # noqa: BLE001 — R-42: остальные плагины тоже должны остановиться
        _log.exception("plugin.shutdown_failed", plugin=one.ctx.name)
