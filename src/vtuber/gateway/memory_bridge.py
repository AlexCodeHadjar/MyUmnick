"""Редактор памяти ↔ UI (S-16.2): после каждого действия UI получает свежий список."""

from collections.abc import Awaitable, Callable

from vtuber.application.memory import MemoryEditor, TransferRequests
from vtuber.domain import MemoryUnavailable
from vtuber.gateway.protocol import OutboundMessage
from vtuber.gateway.protocol_memory import (
    MemoryFactDelete,
    MemoryFacts,
    MemoryFactSave,
    MemoryList,
    MemoryTransfer,
    MemoryTransferred,
)


class MemoryBridge:
    """Список запрашивается только при открытой панели: чтение заметок не должно идти просто так."""

    def __init__(
        self,
        editor: MemoryEditor | None,
        send: Callable[[OutboundMessage], Awaitable[None]],
        transfer: TransferRequests | None = None,
    ) -> None:
        self._editor = editor
        self._send = send
        self._transfer = transfer

    async def handle(
        self, message: MemoryList | MemoryFactSave | MemoryFactDelete | MemoryTransfer
    ) -> None:
        """Выполняет действие и отправляет список; ошибка показывается рядом с ним."""
        if isinstance(message, MemoryTransfer):
            await self._start_transfer()
            return
        if self._editor is None:
            await self._send(MemoryFacts.of([], "Память выключена в настройках"))
            return
        problem = None
        try:
            await self._apply(self._editor, message)
        except (ValueError, MemoryUnavailable) as exc:
            problem = str(exc)
        await self._send_list(self._editor, problem)

    async def _start_transfer(self) -> None:
        """Перевод занимает модель: перенос — в простое, итог придёт отдельным сообщением."""
        if self._transfer is None:
            await self._send(MemoryTransferred.of(None, "memory disabled"))
            return

        async def done(count: int | None, problem: str | None) -> None:
            await self._send(MemoryTransferred.of(count, problem))

        self._transfer.request(done)

    async def _apply(
        self, editor: MemoryEditor, message: MemoryList | MemoryFactSave | MemoryFactDelete
    ) -> None:
        if isinstance(message, MemoryFactSave):
            await editor.update(message.data.note, message.data.text)
        elif isinstance(message, MemoryFactDelete):
            await editor.delete(message.data.note)

    async def _send_list(self, editor: MemoryEditor, problem: str | None) -> None:
        try:
            await self._send(MemoryFacts.of(await editor.facts(), problem))
        except MemoryUnavailable as exc:
            await self._send(MemoryFacts.of([], str(exc)))
