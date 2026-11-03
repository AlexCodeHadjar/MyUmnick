"""WebSocket-сервер шлюза: один клиент-UI, входящие → сервис хода, события шины → клиенту."""

from collections.abc import Awaitable, Callable, Mapping
from types import TracebackType
from typing import Final, Self

from websockets.asyncio.server import Server, ServerConnection, serve
from websockets.exceptions import ConnectionClosed

from vtuber.application.conversation import ConversationService
from vtuber.domain import (
    AudioChunk,
    BackendState,
    BackendStatusChanged,
    CancelReason,
    Component,
    MetricRecorded,
    ProtocolError,
    TurnCancelled,
    TurnFinished,
    TurnStarted,
    ViewerBlocked,
)
from vtuber.gateway.codec import decode_inbound, decode_mic_frame, encode_outbound
from vtuber.gateway.protocol import (
    ChatCancel,
    ChatSend,
    ErrorCode,
    ErrorMessage,
    InputTyping,
    MetricsSpan,
    OutboundMessage,
    Status,
    TurnCancelledMessage,
    TurnFinishedMessage,
    TurnStartedMessage,
    turn_ref,
)
from vtuber.gateway.protocol_extras import (
    ResourcesWatch,
    SetupCancel,
    SetupInstall,
    ViewerBlockedMessage,
)
from vtuber.gateway.resources_feed import ResourcesFeed
from vtuber.gateway.setup_bridge import SetupBridge
from vtuber.gateway.sink import WsReplySink
from vtuber.kernel import ConfigSection, EventBus, get_logger

type MicSink = Callable[[AudioChunk], Awaitable[None]]

REPLACED_CODE: Final = 4000
NS_PER_MS: Final = 1_000_000

_log = get_logger(__name__)


class GatewayConfig(ConfigSection):
    """Секция `[gateway]`: где слушать UI (только localhost, ADR-0002)."""

    host: str
    port: int


class GatewayServer:
    """Шлюз для UI: `async with GatewayServer(...) as server: await server.serve_forever()`.

    Клиент один: новое подключение вытесняет прежнее (код 4000). Отключение посреди хода
    прерывает ход (T-14). Битое сообщение → `error` (`bad_message`), соединение живёт.
    """

    def __init__(self, service: ConversationService, bus: EventBus, cfg: GatewayConfig) -> None:
        self._service = service
        self._cfg = cfg
        self._client: ServerConnection | None = None
        self._server: Server | None = None
        self._statuses: dict[Component, BackendState] = {}
        self._mic: MicSink | None = None
        self._resources: ResourcesFeed | None = None
        self._setup: SetupBridge | None = None
        self._commands: Mapping[str, Callable[[], Awaitable[None]]] = {}
        bus.subscribe(TurnStarted, self._on_started)
        bus.subscribe(TurnFinished, self._on_finished)
        bus.subscribe(TurnCancelled, self._on_cancelled)
        bus.subscribe(MetricRecorded, self._on_metric)
        bus.subscribe(BackendStatusChanged, self._on_status)
        bus.subscribe(ViewerBlocked, self._on_viewer_blocked)

    def use_commands(self, commands: Mapping[str, Callable[[], Awaitable[None]]]) -> None:
        """Команды ведущего от плагинов: точная реплика выполняет команду вместо хода."""
        self._commands = commands

    def use_resources(self, feed: ResourcesFeed) -> None:
        """Снимки менеджера ресурсов для панели UI."""
        self._resources = feed

    def use_setup(self, bridge: SetupBridge) -> None:
        """Мастер первого запуска: UI получает его состояние при подключении."""
        self._setup = bridge

    def on_mic(self, sink: MicSink) -> None:
        """Куда отдавать кадры микрофона; вызов — в цикле чтения сокета, должен быть быстрым."""
        self._mic = sink

    @property
    def has_client(self) -> bool:
        """Подключён ли UI: без него ответ некому показать и озвучить."""
        return self._client is not None

    @property
    def port(self) -> int:
        """Фактический порт (при `port = 0` — выбранный системой)."""
        if self._server is None:
            msg = "GatewayServer не запущен — используйте `async with`"
            raise RuntimeError(msg)
        return int(self._server.sockets[0].getsockname()[1])

    async def __aenter__(self) -> Self:
        self._server = await serve(self._handle, self._cfg.host, self._cfg.port)
        _log.info("gateway.listening", host=self._cfg.host, port=self.port)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

    async def serve_forever(self) -> None:
        """Обслуживает подключения, пока задачу не отменят."""
        if self._server is not None:
            await self._server.serve_forever()

    async def send(self, message: OutboundMessage) -> None:
        """Шлёт сообщение текущему клиенту; нет клиента или он отключился — сообщение теряется."""
        await self._deliver(encode_outbound(message))

    async def send_bytes(self, frame: bytes) -> None:
        """Бинарный кадр (звук) текущему клиенту; без клиента — теряется, как и сообщения."""
        await self._deliver(frame)

    async def _deliver(self, payload: str | bytes) -> None:
        client = self._client
        if client is None:
            return
        try:
            await client.send(payload)
        except ConnectionClosed:
            _log.info("gateway.client_gone")

    async def _handle(self, connection: ServerConnection) -> None:
        previous, self._client = self._client, connection
        if previous is not None:
            await previous.close(REPLACED_CODE, "Подключился другой клиент")
        for component, state in self._statuses.items():
            await self.send(Status.of(component, state))
        if self._setup is not None:
            await self._setup.send_state()
        try:
            async for raw in connection:
                await self._dispatch(raw)
        except ConnectionClosed:
            # В т.ч. код 4000: клиента заменил новый. Обычное завершение, а не сбой обработчика.
            _log.info("gateway.client_closed")
        finally:
            if self._client is connection:
                self._client = None
                if self._resources is not None:
                    self._resources.set_enabled(enabled=False)
                await self._service.cancel(CancelReason.USER_STOP)

    async def _dispatch(self, raw: str | bytes) -> None:
        if isinstance(raw, bytes):
            await self._on_mic_frame(raw)
            return
        try:
            message = decode_inbound(raw)
        except ProtocolError as exc:
            await self.send(ErrorMessage.of(None, ErrorCode.BAD_MESSAGE, str(exc)))
            return
        if isinstance(message, ChatSend):
            await self._on_chat(message.data.text)
        elif isinstance(message, ChatCancel):
            await self._service.cancel(CancelReason.USER_STOP)
        elif isinstance(message, InputTyping):
            # Черновик — только прогрев кэша (T-05): ответа UI не ждёт, шлюз не блокируется.
            self._service.typing(message.data.text)
        else:
            await self._on_panel(message)

    async def _on_panel(self, message: ResourcesWatch | SetupInstall | SetupCancel) -> None:
        if isinstance(message, ResourcesWatch):
            if self._resources is not None:
                self._resources.set_enabled(enabled=message.data.enabled)
        elif self._setup is not None:
            await self._setup.handle(message)

    async def _on_chat(self, text: str) -> None:
        command = self._commands.get(text.strip())
        if command is None:
            await self._service.handle(text, WsReplySink(self.send, self.send_bytes))
            return
        # UI заглушил голос сразу при отправке реплики: ход без звука дописывать незачем.
        await self._service.cancel(CancelReason.USER_STOP)
        try:
            await command()
        except Exception:  # noqa: BLE001 — R-42: команду написал плагин, шлюз должен жить
            _log.exception("gateway.command_failed", command=text)

    async def _on_mic_frame(self, raw: bytes) -> None:
        try:
            frame = decode_mic_frame(raw)
        except ProtocolError as exc:
            await self.send(ErrorMessage.of(None, ErrorCode.BAD_MESSAGE, str(exc)))
            return
        # Без голосового ввода (не загружен, выключен) кадры просто не нужны.
        if self._mic is not None:
            await self._mic(frame.chunk)

    async def _on_viewer_blocked(self, event: ViewerBlocked) -> None:
        await self.send(ViewerBlockedMessage.of(event.author, event.text))

    async def _on_started(self, event: TurnStarted) -> None:
        await self.send(TurnStartedMessage.of(turn_ref(event.turn_id)))

    async def _on_finished(self, event: TurnFinished) -> None:
        await self.send(TurnFinishedMessage.of(turn_ref(event.turn_id)))

    async def _on_cancelled(self, event: TurnCancelled) -> None:
        message = TurnCancelledMessage.of(turn_ref(event.turn_id), event.reason, event.message)
        await self.send(message)

    async def _on_metric(self, event: MetricRecorded) -> None:
        turn = turn_ref(event.turn_id) if event.turn_id is not None else None
        await self.send(MetricsSpan.of(turn, event.name, event.duration_ns / NS_PER_MS))

    async def _on_status(self, event: BackendStatusChanged) -> None:
        self._statuses[event.component] = event.state
        await self.send(Status.of(event.component, event.state))
