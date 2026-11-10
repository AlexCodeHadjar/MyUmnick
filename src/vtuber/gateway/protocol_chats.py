"""Протокол чатов (Этап 21, ADR-0037): список и категории слева в окне, действия над ними."""

from typing import Literal, Self

from vtuber.domain import ChatList
from vtuber.gateway.protocol_base import PROTOCOL_VERSION, ProtocolModel, Version

type ChatVerb = Literal[
    "list",
    "create",
    "open",
    "rename",
    "move",
    "delete",
    "category_create",
    "category_rename",
    "category_delete",
]


class ChatActionData(ProtocolModel):
    """Что сделать: `id` — чат или категория, `name` — название, `category` — куда положить."""

    action: ChatVerb
    id: str | None = None
    name: str | None = None
    category: str | None = None


class ChatAction(ProtocolModel):
    """UI → Ядро: действие со списком чатов."""

    v: Version
    type: Literal["chats.action"]
    data: ChatActionData


class ChatItemData(ProtocolModel):
    """Чат в списке; пустое `title` — «Новый чат» на языке интерфейса."""

    id: str
    title: str
    category: str | None
    updated: str


class CategoryData(ProtocolModel):
    """Категория."""

    id: str
    name: str


class ChatsData(ProtocolModel):
    """Весь список; `switching` — память переключается, ввод лучше подождать."""

    chats: list[ChatItemData]
    categories: list[CategoryData]
    active: str
    switching: bool
    problem: str | None


class ChatsState(ProtocolModel):
    """Ядро → UI: список чатов после любого изменения и при подключении."""

    v: Version = PROTOCOL_VERSION
    type: Literal["chats.state"] = "chats.state"
    data: ChatsData

    @classmethod
    def of(cls, chats: ChatList, *, switching: bool, problem: str | None) -> Self:
        """Состояние из каталога; новые сверху."""
        ordered = sorted(chats.chats, key=lambda chat: chat.updated_at, reverse=True)
        items = [
            ChatItemData(
                id=chat.id,
                title=chat.title,
                category=chat.category,
                updated=chat.updated_at.isoformat(),
            )
            for chat in ordered
        ]
        categories = [CategoryData(id=one.id, name=one.name) for one in chats.categories]
        data = ChatsData(
            chats=items,
            categories=categories,
            active=chats.active,
            switching=switching,
            problem=problem,
        )
        return cls(data=data)
