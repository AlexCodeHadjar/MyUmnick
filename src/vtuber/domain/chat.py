"""Чаты (Этап 21, ADR-0037): у каждого своя память и свой контекст; категории — папки для чатов."""

import re
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Final

MAIN_CHAT: Final = "main"
"""Чат, который был до появления чатов: его память лежит по прежним путям (профиль по умолчанию)."""
_ID: Final = re.compile(r"^[a-z0-9-]{1,40}$")
MAX_TITLE: Final = 60


def is_chat_id(value: str) -> bool:
    """Идентификатор годится в имя папки и файла: без путей и особых символов."""
    return bool(_ID.match(value))


@dataclass(frozen=True, slots=True)
class ChatInfo:
    """Чат в списке; `title` пустой — ещё не было реплик («Новый чат» в UI)."""

    id: str
    title: str
    category: str | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ChatCategory:
    """Категория, которую создал пользователь."""

    id: str
    name: str


@dataclass(frozen=True, slots=True)
class ChatList:
    """Весь каталог: чаты, категории и активный чат."""

    chats: tuple[ChatInfo, ...]
    categories: tuple[ChatCategory, ...]
    active: str = MAIN_CHAT

    def chat(self, chat_id: str) -> ChatInfo | None:
        """Чат по идентификатору."""
        return next((chat for chat in self.chats if chat.id == chat_id), None)

    def with_chat(self, chat: ChatInfo) -> "ChatList":
        """Каталог с заменённым или добавленным чатом."""
        others = tuple(one for one in self.chats if one.id != chat.id)
        return replace(self, chats=(chat, *others))


def chat_title(text: str) -> str:
    """Название чата из первой реплики: одна строка, не длиннее `MAX_TITLE`."""
    line = " ".join(text.split())
    return line if len(line) <= MAX_TITLE else line[: MAX_TITLE - 1].rstrip() + "…"
