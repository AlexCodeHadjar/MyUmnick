"""Каталог чатов (Этап 21, ADR-0037): что пользователь делает со списком и что из этого следует.

Переключение памяти — не здесь: каталог говорит, какой чат активен, а память меняет bootstrap
(`ChatSwitcher`). Каталог пишется на диск после каждого изменения, ход его не ждёт.
"""

import secrets
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Final

from vtuber.domain import (
    MAIN_CHAT,
    ChatCategory,
    ChatInfo,
    ChatList,
    TurnRemembered,
    chat_title,
)
from vtuber.kernel import EventBus, get_logger
from vtuber.ports import ChatCatalogPort

type Clock = Callable[[], datetime]
type Listener = Callable[[ChatList], Awaitable[None]]

MAX_NAME: Final = 40
_log = get_logger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return secrets.token_hex(4)


class ChatDirectory:
    """Список чатов и категорий; `changed` — кому сообщать о новом состоянии (UI)."""

    def __init__(self, catalog: ChatCatalogPort, chats: ChatList, clock: Clock = _now) -> None:
        self._catalog = catalog
        self._chats = chats
        self._clock = clock
        self.changed: Listener | None = None

    @property
    def chats(self) -> ChatList:
        """Текущий каталог."""
        return self._chats

    def follow(self, bus: EventBus) -> None:
        """Первая реплика даёт чату название; любая — поднимает его вверх списка."""
        bus.subscribe(TurnRemembered, self._on_turn)

    async def create(self, category: str | None) -> str:
        """Новый пустой чат (ещё не активный); возвращает его идентификатор."""
        chat = ChatInfo(_new_id(), "", self._category(category), self._clock())
        await self._commit(self._chats.with_chat(chat))
        return chat.id

    async def rename(self, chat_id: str, title: str) -> None:
        """Своё название чата."""
        chat = self._require(chat_id)
        await self._commit(self._chats.with_chat(replace(chat, title=chat_title(title))))

    async def move(self, chat_id: str, category: str | None) -> None:
        """Перенести чат в категорию (None — без категории)."""
        chat = self._require(chat_id)
        await self._commit(self._chats.with_chat(replace(chat, category=self._category(category))))

    async def remove(self, chat_id: str) -> None:
        """Убрать чат из списка; память стирает порт. Активный и основной чат не удаляются.

        Raises:
            ValueError: чат активен, основной или не найден.

        """
        self._require(chat_id)
        if chat_id in {MAIN_CHAT, self._chats.active}:
            msg = "Этот чат сейчас открыт или основной: его нельзя удалить"
            raise ValueError(msg)
        await self._catalog.erase(chat_id)
        chats = tuple(chat for chat in self._chats.chats if chat.id != chat_id)
        await self._commit(replace(self._chats, chats=chats))

    async def activate(self, chat_id: str) -> None:
        """Отметить чат открытым (память уже переключена)."""
        self._require(chat_id)
        await self._commit(replace(self._chats, active=chat_id))

    async def add_category(self, name: str) -> str:
        """Новая категория; возвращает её идентификатор."""
        category = ChatCategory(_new_id(), _name(name))
        await self._commit(replace(self._chats, categories=(*self._chats.categories, category)))
        return category.id

    async def rename_category(self, category_id: str, name: str) -> None:
        """Новое имя категории."""
        self._require_category(category_id)
        categories = tuple(
            replace(one, name=_name(name)) if one.id == category_id else one
            for one in self._chats.categories
        )
        await self._commit(replace(self._chats, categories=categories))

    async def remove_category(self, category_id: str) -> None:
        """Удалить категорию; её чаты остаются, просто без категории."""
        self._require_category(category_id)
        categories = tuple(one for one in self._chats.categories if one.id != category_id)
        chats = tuple(
            replace(chat, category=None) if chat.category == category_id else chat
            for chat in self._chats.chats
        )
        await self._commit(ChatList(chats, categories, self._chats.active))

    async def _on_turn(self, event: TurnRemembered) -> None:
        chat = self._chats.chat(self._chats.active)
        if chat is None or event.turn.is_private:
            return
        title = chat.title or chat_title(event.turn.user_text)
        await self._commit(
            self._chats.with_chat(replace(chat, title=title, updated_at=self._clock()))
        )

    async def _commit(self, chats: ChatList) -> None:
        self._chats = chats
        await self._catalog.save(chats)
        if self.changed is not None:
            await self.changed(chats)

    def _category(self, category: str | None) -> str | None:
        if category is None:
            return None
        self._require_category(category)
        return category

    def _require(self, chat_id: str) -> ChatInfo:
        chat = self._chats.chat(chat_id)
        if chat is None:
            msg = f"Нет такого чата: {chat_id}"
            raise ValueError(msg)
        return chat

    def _require_category(self, category_id: str) -> None:
        if all(one.id != category_id for one in self._chats.categories):
            msg = f"Нет такой категории: {category_id}"
            raise ValueError(msg)


def _name(name: str) -> str:
    clean = " ".join(name.split())[:MAX_NAME]
    if not clean:
        msg = "Название категории пустое"
        raise ValueError(msg)
    return clean
