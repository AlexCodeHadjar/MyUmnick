"""Список чатов ↔ UI (Этап 21, ADR-0037): действия пользователя → каталог; смена чата → память."""

import asyncio
from collections.abc import Awaitable, Callable

from vtuber.application.chats import ChatDirectory
from vtuber.domain import ChatList, MemoryUnavailable
from vtuber.gateway.protocol import OutboundMessage
from vtuber.gateway.protocol_chats import ChatAction, ChatActionData, ChatsState
from vtuber.kernel import get_logger

type Switch = Callable[[str], Awaitable[None]]
"""Открыть чат: закрыть память прежнего, открыть память нового и показать его историю."""

_log = get_logger(__name__)


class ChatsBridge:
    """Пока чат переключается, новые действия ждут: две смены сразу память не выдержит."""

    def __init__(
        self,
        directory: ChatDirectory,
        switch: Switch,
        send: Callable[[OutboundMessage], Awaitable[None]],
    ) -> None:
        self._directory = directory
        self._switch = switch
        self._send = send
        self._lock = asyncio.Lock()
        self._switching = False
        directory.changed = self._on_changed

    async def send_state(self, problem: str | None = None) -> None:
        """Список целиком: при подключении и после ошибки."""
        await self._send(
            ChatsState.of(self._directory.chats, switching=self._switching, problem=problem)
        )

    async def handle(self, message: ChatAction) -> None:
        """Выполняет действие; ошибка показывается под списком, соединение живёт."""
        async with self._lock:
            try:
                await self._apply(message.data)
            except (ValueError, MemoryUnavailable) as exc:
                await self.send_state(str(exc))

    async def _apply(self, data: ChatActionData) -> None:
        if data.action == "list":
            await self.send_state()
        elif data.action in {"create", "open"}:
            await self._open(data)
        elif data.action.startswith("category"):
            await self._category(data)
        else:
            await self._chat(data)

    async def _open(self, data: ChatActionData) -> None:
        if data.action == "create":
            chat_id = await self._directory.create(data.category)
        else:
            chat_id = _required(data.id)
        if chat_id == self._directory.chats.active:
            await self.send_state()
            return
        self._switching = True
        await self.send_state()
        try:
            await self._switch(chat_id)
            await self._directory.activate(chat_id)
        finally:
            self._switching = False
        await self.send_state()

    async def _chat(self, data: ChatActionData) -> None:
        chat_id = _required(data.id)
        if data.action == "rename":
            await self._directory.rename(chat_id, _required(data.name))
        elif data.action == "move":
            await self._directory.move(chat_id, data.category)
        elif data.action == "delete":
            await self._directory.remove(chat_id)

    async def _category(self, data: ChatActionData) -> None:
        if data.action == "category_create":
            await self._directory.add_category(_required(data.name))
        elif data.action == "category_rename":
            await self._directory.rename_category(_required(data.id), _required(data.name))
        else:
            await self._directory.remove_category(_required(data.id))

    async def _on_changed(self, _: ChatList) -> None:
        await self.send_state()


def _required(value: str | None) -> str:
    if value is None or not value.strip():
        msg = "В действии с чатом не хватает поля"
        raise ValueError(msg)
    return value
