"""Загрузка плагинов (Этап 12): entry points `vtuber.plugins`, включённые в `[plugins].enabled`.

Плагин — чужой код: сбой при загрузке, старте или остановке пишется в лог и не мешает приложению.
Ни один плагин не включён — нет ни поиска пакетов, ни задач, ни подписок. С Этапа 23 (ADR-0043)
плагин можно запустить и на ходу — из панели «Навыки»: его справка, команды и источники
дописываются в живые списки, которые читает ядро.
"""

import asyncio
from collections.abc import AsyncIterator, Callable, Iterable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from importlib.metadata import EntryPoint, entry_points
from typing import Final

from vtuber.application.scheduler import ModelSpec, Priority, ResourceManager
from vtuber.domain import ConfigError, SkillInfo, plugin_skill
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
type SourceSink = Callable[[MessageStream, str], None]
"""Новый источник реплик (плагин включили на ходу): ядро начинает его читать."""

_log = get_logger(__name__)


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


@dataclass(frozen=True, slots=True)
class PluginEnv:
    """С чем плагины стартуют: секция конфига, шина, видеопамять, язык издания."""

    cfg: PluginsConfig
    bus: EventBus
    discover: Discover = lambda: entry_points(group=ENTRY_POINT_GROUP)
    models: ModelHost | None = None
    language: str = "ru"


class PluginServices:
    """Что плагины дали ядру: живые списки — ядро читает их на каждой реплике."""

    def __init__(self, env: PluginEnv) -> None:
        self._env = env
        self.contexts: list[ContextTool] = []
        self.commands: dict[str, Command] = {}
        self.command_skills: dict[str, str] = {}
        self.sources: list[tuple[MessageStream, str]] = []
        self.skills: list[SkillInfo] = []
        self.on_source: SourceSink | None = None
        self._found: dict[str, EntryPoint] | None = None
        self._started: list[_Started] = []
        self._pumps: list[asyncio.Task[None]] = []

    @property
    def running(self) -> frozenset[str]:
        """Имена запущенных плагинов."""
        return frozenset(one.ctx.name for one in self._started)

    async def load(self, name: str) -> tuple[SkillInfo, ...] | None:
        """Запустить плагин `name`; вернёт его навыки или `None`, если он не запустился."""
        if name in self.running:
            return tuple(info for info in self.skills if info.plugin == name)
        env = self._env
        found = await self._entries()
        ctx = PluginContext(name, env.bus, env.cfg.settings.get(name, {}), env.models, env.language)
        one = await _start(found.get(name), env.cfg, ctx)
        if one is None:
            return None
        self._started.append(one)
        self._pumps.append(asyncio.create_task(ctx.run()))
        self._take(ctx)
        return ctx.skills

    async def available(self) -> tuple[SkillInfo, ...]:
        """Установленные, но не запущенные плагины — навыками «весь плагин» для панели."""
        found = await self._entries()
        return tuple(
            plugin_skill(name, summary=_summary(point))
            for name, point in sorted(found.items())
            if name not in self.running
        )

    async def aclose(self) -> None:
        """Остановить всё в обратном порядке запуска."""
        for pump in self._pumps:
            pump.cancel()
        await asyncio.gather(*self._pumps, return_exceptions=True)
        for one in reversed(self._started):
            await _stop(one, self._env.cfg.shutdown_timeout_s)

    def _take(self, ctx: PluginContext) -> None:
        self.contexts.extend(ctx.contexts)
        self.commands.update(ctx.commands)
        self.command_skills.update(ctx.command_skills)
        self.skills.extend(ctx.skills)
        for stream, skill in ctx.skilled_sources:
            self.sources.append((stream, skill))
            if self.on_source is not None:
                self.on_source(stream, skill)

    async def _entries(self) -> dict[str, EntryPoint]:
        if self._found is None:
            # Поиск пакетов читает метаданные с диска — не в цикле событий (R-34).
            points = await asyncio.to_thread(lambda: list(self._env.discover()))
            self._found = {point.name: point for point in points}
        return self._found


@asynccontextmanager
async def running_plugins(
    env: PluginEnv, wanted: Iterable[str] = ()
) -> AsyncIterator[PluginServices]:
    """Включённые (в конфиге и в панели «Навыки» — `wanted`) плагины работают на время контекста.

    Остановка — в обратном порядке. Ничего не включено — нет даже поиска пакетов.
    """
    services = PluginServices(env)
    for name in dict.fromkeys([*env.cfg.enabled, *wanted]):
        await services.load(name)
    try:
        yield services
    finally:
        await services.aclose()


def _summary(point: EntryPoint) -> str:
    dist = point.dist
    return "" if dist is None else str(dist.metadata.get("Summary") or "")


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
        # Плагин объявляет языки атрибутом `languages`; нет его — только русский (Этап 20).
        languages = getattr(plugin, "languages", ("ru",))
        if ctx.language not in languages:
            _log.warning("plugin.language_unsupported", plugin=name, language=ctx.language)
            return None
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
