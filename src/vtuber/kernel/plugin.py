"""Контракт плагина: всё, что сторонний код видит в ядре, — `PluginContext` (FR-14, Этап 12)."""

import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable, Mapping
from functools import partial
from typing import Final, Protocol, runtime_checkable

from pydantic import Field, ValidationError

from vtuber.domain import ConfigError, IncomingMessage
from vtuber.kernel.bus import EventBus, Handler
from vtuber.kernel.config import ConfigSection
from vtuber.kernel.logging import get_logger

MAX_PENDING_PLUGIN_EVENTS: Final = 256
"""Очередь одного плагина: зависший плагин теряет свои события, а не память процесса."""

type MessageStream = Callable[[], AsyncGenerator[IncomingMessage]]
"""Источник реплик: следующую реплику ядро запрашивает, когда готово на неё ответить."""

type ContextProvider = Callable[[str], Awaitable[str | None]]
"""Справка хода по реплике, до запроса к LLM; должна успеть за `context_timeout_s`."""

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


class PluginContext:
    """Доступ плагина к ядру: подписка на события, своя секция конфига, логгер.

    Обработчики плагина идут из своей очереди, а не внутри `publish`: издатель (сервис хода) ждёт
    подписчиков шины, и медленный плагин задерживал бы начало ответа (приоритет 1, T-15).
    """

    def __init__(self, name: str, bus: EventBus, settings: Mapping[str, object]) -> None:
        self.name = name
        self.log = get_logger(f"plugin.{name}")
        self._bus = bus
        self._settings = settings
        self._pending: asyncio.Queue[Callable[[], Awaitable[None]]] = asyncio.Queue(
            MAX_PENDING_PLUGIN_EVENTS
        )
        self._closed = False
        self._sources: list[MessageStream] = []
        self._contexts: list[ContextProvider] = []

    def subscribe[E](self, event_type: type[E], handler: Handler[E]) -> None:
        """Подписывает `handler`; события одного плагина обрабатываются строго по очереди."""

        async def enqueue(event: E) -> None:
            self._offer(partial(handler, event))

        self._bus.subscribe(event_type, enqueue)

    def add_source(self, stream: MessageStream) -> None:
        """Реплики из `stream` становятся ходами диалога (только в режиме `serve`)."""
        self._sources.append(stream)

    @property
    def sources(self) -> tuple[MessageStream, ...]:
        """Зарегистрированные источники реплик."""
        return tuple(self._sources)

    def add_context(self, provider: ContextProvider) -> None:
        """Строка от `provider` попадает в справку хода: инструмент срабатывает до генерации."""
        self._contexts.append(provider)

    @property
    def contexts(self) -> tuple[ContextProvider, ...]:
        """Зарегистрированные поставщики справки."""
        return tuple(self._contexts)

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
