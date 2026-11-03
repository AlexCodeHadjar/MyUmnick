"""Реплики из источников плагинов → ходы диалога, в отличие от чата UI — без перебивания."""

import asyncio
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import aclosing

from vtuber.application.conversation import ConversationService
from vtuber.domain import IncomingMessage, looks_like_attack, viewer_line
from vtuber.gateway.protocol import InputFinal, OutboundMessage
from vtuber.gateway.protocol_extras import ViewerBlockedMessage
from vtuber.gateway.sink import WsReplySink
from vtuber.kernel import get_logger

_log = get_logger(__name__)


class ExternalTurns:
    """Отвечает на реплики по одной и только в тишине: зритель не обрывает речь витюбера.

    Следующая реплика запрашивается у источника, лишь когда ответ на прошлую прозвучал: источник
    выбирает, на что отвечать, в этот момент, а не заранее. Чат UI идёт мимо этой очереди: лишний
    шаг в горячем пути ему не нужен, и его реплика перебивает ответ зрителю (приоритет ведущего).
    """

    def __init__(
        self,
        service: ConversationService,
        send: Callable[[OutboundMessage], Awaitable[None]],
        send_bytes: Callable[[bytes], Awaitable[None]],
        has_client: Callable[[], bool],
    ) -> None:
        self._service = service
        self._send = send
        self._send_bytes = send_bytes
        self._has_client = has_client
        self._one_at_a_time = asyncio.Lock()

    async def run(self, stream: Callable[[], AsyncGenerator[IncomingMessage]]) -> None:
        """Читает источник, пока задачу не отменят; сбой источника не трогает приложение."""
        try:
            async with aclosing(stream()) as messages:
                async for message in messages:
                    await self._answer(message)
        except Exception:  # noqa: BLE001 — R-42: источник — чужой код, диалог продолжается
            _log.exception("external.source_failed")

    async def _answer(self, message: IncomingMessage) -> None:
        if not self._has_client():
            # Ответ никто не услышит, а в истории и памяти он остался бы.
            _log.info("external.no_client", source=message.source)
            return
        # Вторая линия: источник мог и не фильтровать, а до модели атака дойти не должна (FR-31).
        if message.is_viewer and looks_like_attack(message.text):
            _log.warning("external.viewer_blocked", author=message.author)
            await self._send(ViewerBlockedMessage.of(message.author, message.text))
            return
        async with self._one_at_a_time:
            await self._service.wait_silent()
            plain = f"{message.author}: {message.text}"
            await self._send(InputFinal.of(plain))
            text = viewer_line(message.author, message.text) if message.is_viewer else plain
            sink = WsReplySink(self._send, self._send_bytes)
            await self._service.handle(text, sink, external=True)
            await self._service.wait_silent()
