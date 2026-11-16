"""Контракт плагина: всё, что сторонний код видит в ядре, — `PluginContext` (FR-14, Этап 12)."""

import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable, Mapping, Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, replace
from functools import partial
from typing import Final, Protocol, runtime_checkable

from pydantic import Field, ValidationError

from vtuber.domain import (
    AudioChunk,
    ConfigError,
    IncomingMessage,
    PerformanceRequested,
    SearchSource,
    SkillInfo,
    SourcesFound,
    TextShown,
    ViewerBlocked,
    plugin_skill,
)
from vtuber.kernel.bus import EventBus, Handler
from vtuber.kernel.config import ConfigSection
from vtuber.kernel.logging import get_logger

MAX_PENDING_PLUGIN_EVENTS: Final = 256
"""Очередь одного плагина: зависший плагин теряет свои события, а не память процесса."""

type MessageStream = Callable[[], AsyncGenerator[IncomingMessage]]
"""Источник реплик: следующую реплику ядро запрашивает, когда готово на неё ответить."""

type ContextProvider = Callable[[str], Awaitable[str | None]]
"""Справка хода по реплике, до запроса к LLM; должна успеть за `context_timeout_s`."""


@dataclass(frozen=True, slots=True)
class ContextTool:
    """Инструмент, его срок (`None` — обычный короткий срок из `[plugins]`) и навык (ADR-0043)."""

    provider: ContextProvider
    timeout_s: float | None = None
    skill: str = ""


type Command = Callable[[], Awaitable[None]]
"""Команда ведущего: выполняется вместо хода, если реплика точно совпала с её текстом."""

_log = get_logger(__name__)


class PluginsConfig(ConfigSection):
    """Секция `[plugins]`: что включено и настройки каждого плагина в `settings.<имя>`.

    Невключённый плагин даже не импортируется — на задержки он не влияет (критерий Этапа 12).
    """

    enabled: tuple[str, ...]
    setup_timeout_s: float = Field(gt=0)
    shutdown_timeout_s: float = Field(gt=0)
    context_timeout_s: float = Field(gt=0)
    settings: dict[str, dict[str, object]]


class LoadableModel(Protocol):
    """Модель, которую можно загрузить в видеопамять и выгрузить."""

    async def load(self) -> None:
        """Загрузить."""
        ...

    async def unload(self) -> None:
        """Выгрузить и освободить память."""
        ...


class ModelHost(Protocol):
    """Менеджер видеопамяти для плагинов; сам он живёт выше ядра (ADR-0005)."""

    def hold(
        self, name: str, vram_mb: int, model: LoadableModel
    ) -> Callable[[], AbstractAsyncContextManager[None]]:
        """Поставить модель на учёт; вызов результата — модель в памяти на время блока."""
        ...


class PluginContext:
    """Доступ плагина к ядру: подписка на события, своя секция конфига, логгер.

    Обработчики плагина идут из своей очереди, а не внутри `publish`: издатель (сервис хода) ждёт
    подписчиков шины, и медленный плагин задерживал бы начало ответа (приоритет 1, T-15).
    """

    def __init__(
        self,
        name: str,
        bus: EventBus,
        settings: Mapping[str, object],
        models: ModelHost | None = None,
        language: str = "ru",
    ) -> None:
        self.name = name
        self.models = models
        # Язык издания (Этап 20, ADR-0032): плагин говорит с персоной на нём.
        self.language = language
        self.log = get_logger(f"plugin.{name}")
        self._bus = bus
        self._settings = settings
        self._pending: asyncio.Queue[Callable[[], Awaitable[None]]] = asyncio.Queue(
            MAX_PENDING_PLUGIN_EVENTS
        )
        self._closed = False
        self._sources: list[tuple[MessageStream, str]] = []
        self._contexts: list[ContextTool] = []
        self._commands: dict[str, Command] = {}
        self._command_skills: dict[str, str] = {}
        self._skills: dict[str, SkillInfo] = {}

    def declare_skill(self, info: SkillInfo) -> str:
        """Объявить навык для панели «Навыки» (ADR-0043); вернёт полный id `<плагин>.<id>`.

        `info.id` — короткое имя внутри плагина («timer»), `info.plugin` заполняет ядро. Полный id
        передают в `skill=` у `add_context`, `add_command`, `add_source`; без `skill=` всё
        зарегистрированное — один навык с id = имя плагина.
        """
        full = replace(info, id=f"{self.name}.{info.id}", plugin=self.name)
        self._skills[full.id] = full
        return full.id

    @property
    def skills(self) -> tuple[SkillInfo, ...]:
        """Навыки плагина: объявленные и навык «весь плагин», если на него что-то записано."""
        used = {tool.skill for tool in self._contexts}
        used |= set(self._command_skills.values()) | {skill for _, skill in self._sources}
        whole = (plugin_skill(self.name),) if self.name in used or not self._skills else ()
        return whole + tuple(self._skills.values())

    def _skill(self, skill: str | None) -> str:
        return self.name if skill is None else skill

    def subscribe[E](self, event_type: type[E], handler: Handler[E]) -> None:
        """Подписывает `handler`; события одного плагина обрабатываются строго по очереди."""

        async def enqueue(event: E) -> None:
            self._offer(partial(handler, event))

        self._bus.subscribe(event_type, enqueue)

    def add_source(self, stream: MessageStream, *, skill: str | None = None) -> None:
        """Реплики из `stream` становятся ходами диалога (только в режиме `serve`)."""
        self._sources.append((stream, self._skill(skill)))

    @property
    def sources(self) -> tuple[MessageStream, ...]:
        """Зарегистрированные источники реплик."""
        return tuple(stream for stream, _ in self._sources)

    @property
    def skilled_sources(self) -> tuple[tuple[MessageStream, str], ...]:
        """Источники вместе с навыком: выключенный навык — реплики не идут."""
        return tuple(self._sources)

    def add_context(
        self,
        provider: ContextProvider,
        *,
        timeout_s: float | None = None,
        skill: str | None = None,
    ) -> None:
        """Строка от `provider` попадает в справку хода: инструмент срабатывает до генерации.

        Свой `timeout_s` нужен только долгому инструменту; ждать его будет лишь реплика, на которую
        он сам решит работать, остальные он пропускает сразу.
        """
        self._contexts.append(ContextTool(provider, timeout_s, self._skill(skill)))

    async def perform(self, title: str, audio: AsyncGenerator[AudioChunk]) -> None:
        """Исполнить готовый звук ходом без модели; прерывается, как обычный ответ."""
        await self._bus.publish(PerformanceRequested(title, audio))

    async def show_text(self, title: str, text: str) -> None:
        """Показать текст в чате мимо голоса: например, код."""
        await self._bus.publish(TextShown(title, text))

    async def report_sources(self, sources: Sequence[SearchSource]) -> None:
        """Показать ведущему, откуда взят ответ."""
        await self._bus.publish(SourcesFound(tuple(sources)))

    @property
    def contexts(self) -> tuple[ContextTool, ...]:
        """Зарегистрированные поставщики справки."""
        return tuple(self._contexts)

    def add_command(self, text: str, command: Command, *, skill: str | None = None) -> None:
        """Реплика ведущего, в точности равная `text`, вызовет `command` и до модели не дойдёт."""
        self._commands[text] = command
        self._command_skills[text] = self._skill(skill)

    @property
    def command_skills(self) -> Mapping[str, str]:
        """Навык каждой команды: выключенный навык — реплика идёт к модели как обычная."""
        return self._command_skills

    @property
    def commands(self) -> Mapping[str, Command]:
        """Зарегистрированные команды ведущего."""
        return self._commands

    async def report_blocked(self, author: str, text: str) -> None:
        """Сообщить ведущему о заблокированной реплике; общей публикации в шину у плагина нет."""
        await self._bus.publish(ViewerBlocked(author, text))

    def settings[T: ConfigSection](self, model: type[T]) -> T:
        """Настройки плагина из `[plugins.settings.<имя>]`, проверенные моделью `model`.

        Raises:
            ConfigError: значение не проходит проверку.

        """
        try:
            return model.model_validate(self._settings)
        except ValidationError as exc:
            msg = f"Секция [plugins.settings.{self.name}]: {exc} — исправьте конфиг"
            raise ConfigError(msg) from exc

    async def run(self) -> None:
        """Обрабатывает события, пока задачу не отменят; ошибка обработчика остаётся в логе."""
        while True:
            call = await self._pending.get()
            try:
                await call()
            except Exception:  # noqa: BLE001 — R-42: граница плагина, ядро не должно упасть
                _log.exception("plugin.handler_failed", plugin=self.name)

    def close(self) -> None:
        """Больше не принимать события: подписку у шины снять нельзя, она становится пустой."""
        self._closed = True

    def _offer(self, call: Callable[[], Awaitable[None]]) -> None:
        if self._closed:
            return
        try:
            self._pending.put_nowait(call)
        except asyncio.QueueFull:
            _log.warning("plugin.event_dropped", plugin=self.name)


@runtime_checkable
class Plugin(Protocol):
    """Плагин: entry point группы `vtuber.plugins` указывает на его класс или фабрику."""

    @property
    def name(self) -> str:
        """Имя плагина; совпадает с именем entry point и секцией настроек."""
        ...

    async def setup(self, ctx: PluginContext) -> None:
        """Подписаться на события и запустить своё; ошибка — плагин выключен, ядро работает."""
        ...

    async def shutdown(self) -> None:
        """Остановить и освободить запущенное в `setup`."""
        ...
