"""Приватный режим и очистка памяти ↔ UI (S-17.2)."""

from collections.abc import Awaitable, Callable

from vtuber.application.conversation import ConversationService
from vtuber.application.memory import MemoryEraser
from vtuber.domain import CancelReason, VtuberError
from vtuber.gateway.protocol import OutboundMessage
from vtuber.gateway.protocol_memory import (
    MemoryErase,
    MemoryErased,
    PrivacySet,
    PrivacyState,
)


class PrivacyBridge:
    """Режим держит сервис хода, а UI получает его состояние при каждом подключении."""

    def __init__(
        self,
        service: ConversationService,
        eraser: MemoryEraser | None,
        send: Callable[[OutboundMessage], Awaitable[None]],
    ) -> None:
        self._service = service
        self._eraser = eraser
        self._send = send

    async def send_state(self) -> None:
        """Перезапуск окна не должен скрыть, что разговор не запоминается."""
        available = self._eraser is not None
        await self._send(PrivacyState.of(enabled=self._service.private, erasable=available))

    async def handle(self, message: PrivacySet | MemoryErase) -> None:
        """Переключить режим или очистить память; без `confirm` очистка не выполняется."""
        if isinstance(message, PrivacySet):
            self._service.set_private(enabled=message.data.enabled)
            await self.send_state()
        else:
            await self._erase(confirm=message.data.confirm)

    async def _erase(self, *, confirm: bool) -> None:
        if not confirm:
            await self._send(MemoryErased.of("Очистка не подтверждена, память не тронута"))
        elif self._eraser is None:
            await self._send(MemoryErased.of("Память выключена в настройках: очищать нечего"))
        else:
            await self._service.cancel(CancelReason.USER_STOP)
            try:
                await self._eraser.erase()
            except VtuberError as exc:
                await self._send(MemoryErased.of(f"Очистить не удалось: {exc}"))
            else:
                await self._send(MemoryErased.of(None))
