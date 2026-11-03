"""Загрузка плагинов (Этап 12): entry points `vtuber.plugins`, включённые в `[plugins].enabled`.

Плагин — чужой код: сбой при загрузке, старте или остановке пишется в лог и не мешает приложению.
Ни один плагин не включён — нет ни поиска пакетов, ни задач, ни подписок.
"""

import asyncio
from collections.abc import AsyncIterator, Callable, Iterable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from importlib.metadata import EntryPoint, entry_points
from typing import Final

from vtuber.domain import ConfigError
from vtuber.kernel import EventBus, MessageStream, Plugin, PluginContext, PluginsConfig, get_logger

ENTRY_POINT_GROUP: Final = "vtuber.plugins"

type Discover = Callable[[], Iterable[EntryPoint]]

_log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class _Started:
    plugin: Plugin
    ctx: PluginContext


def _installed() -> Iterable[EntryPoint]:
    return entry_points(group=ENTRY_POINT_GROUP)


@asynccontextmanager
async def running_plugins(
    cfg: PluginsConfig, bus: EventBus, discover: Discover = _installed
) -> AsyncIterator[tuple[MessageStream, ...]]:
    """Включённые плагины работают на время контекста; остановка — в обратном порядке.

    Отдаёт источники реплик, которые плагины зарегистрировали в `setup`.
    """
    if not cfg.enabled:
        yield ()
        return
    found = {point.name: point for point in discover()}
    attempts = [await _start(name, found.get(name), cfg, bus) for name in cfg.enabled]
    started = [one for one in attempts if one is not None]
    pumps = [asyncio.create_task(one.ctx.run()) for one in started]
    try:
        yield tuple(stream for one in started for stream in one.ctx.sources)
    finally:
        for pump in pumps:
            pump.cancel()
        await asyncio.gather(*pumps, return_exceptions=True)
        for one in reversed(started):
            await _stop(one, cfg.shutdown_timeout_s)


async def _start(
    name: str, point: EntryPoint | None, cfg: PluginsConfig, bus: EventBus
) -> _Started | None:
    if point is None:
        # Не ошибка конфига: снятый пакет не должен лишать пользователя приложения.
        _log.warning("plugin.not_installed", plugin=name)
        return None
    ctx = PluginContext(name, bus, cfg.settings.get(name, {}))
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
