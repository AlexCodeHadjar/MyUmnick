"""Порт каталога чатов (Этап 21): где лежит список чатов и категорий и как стереть данные чата."""

from typing import Protocol

from vtuber.domain import ChatList


class ChatCatalogPort(Protocol):
    """Каталог чатов издания. Ошибки доступа к диску — `MemoryUnavailable`."""

    async def load(self) -> ChatList:
        """Сохранённый каталог; нет файла — каталог с одним основным чатом."""
        ...

    async def save(self, chats: ChatList) -> None:
        """Записать каталог целиком (атомарно)."""
        ...

    async def erase(self, chat_id: str) -> None:
        """Стереть память удалённого чата: базу фактов и заметки. Основной чат не стирается."""
        ...
