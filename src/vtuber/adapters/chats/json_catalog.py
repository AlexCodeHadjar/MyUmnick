"""Каталог чатов в JSON рядом с памятью издания (Этап 21, ADR-0037): `data/chats.json`."""

import asyncio
import json
import shutil
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from vtuber.domain import (
    MAIN_CHAT,
    ChatCategory,
    ChatInfo,
    ChatList,
    MemoryUnavailable,
    is_chat_id,
)

type Locate = Callable[[str], tuple[Path, Path]]
"""Чат → (файл базы фактов, папка заметок) — пути его памяти."""

_SQLITE_SIDECARS = ("-wal", "-shm", "-journal")


class JsonChatCatalog:
    """Реализует `ChatCatalogPort`; файл пишется через временный — сбой не оставит битый каталог."""

    def __init__(self, path: Path, locate: Locate) -> None:
        self._path = path
        self._locate = locate

    async def load(self) -> ChatList:
        """Каталог с диска; нет файла или он битый — один основной чат."""
        return await asyncio.to_thread(self._load)

    async def save(self, chats: ChatList) -> None:
        """Записать каталог."""
        try:
            await asyncio.to_thread(self._save, chats)
        except OSError as exc:
            msg = f"Каталог чатов {self._path} не записывается: {exc}"
            raise MemoryUnavailable(msg) from exc

    async def erase(self, chat_id: str) -> None:
        """Стереть базу фактов и заметки чата. Основной чат и чужие пути не трогаются."""
        if chat_id == MAIN_CHAT or not is_chat_id(chat_id):
            return
        store, vault = self._locate(chat_id)
        try:
            await asyncio.to_thread(_erase, store, vault)
        except OSError as exc:
            msg = f"Память чата {chat_id} не стёрлась: {exc}"
            raise MemoryUnavailable(msg) from exc

    def _load(self) -> ChatList:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            return _parse(raw)
        except (OSError, ValueError, KeyError, TypeError):
            return _fresh()

    def _save(self, chats: ChatList) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".tmp")
        text = json.dumps(_dump(chats), ensure_ascii=False, indent=1)
        temporary.write_text(text, encoding="utf-8", newline="\n")
        temporary.replace(self._path)


def _fresh() -> ChatList:
    return ChatList((ChatInfo(MAIN_CHAT, "", None, datetime.now().astimezone()),), ())


def _parse(raw: dict[str, object]) -> ChatList:
    categories = tuple(
        ChatCategory(str(item["id"]), str(item["name"]))
        for item in _items(raw["categories"])
        if is_chat_id(str(item["id"]))
    )
    known = {category.id for category in categories}
    chats = tuple(
        ChatInfo(
            str(item["id"]),
            str(item["title"]),
            str(item["category"]) if item.get("category") in known else None,
            datetime.fromisoformat(str(item["updated_at"])),
        )
        for item in _items(raw["chats"])
        if is_chat_id(str(item["id"]))
    )
    if all(chat.id != MAIN_CHAT for chat in chats):
        chats = (*_fresh().chats, *chats)
    active = str(raw.get("active", MAIN_CHAT))
    return ChatList(chats, categories, active if any(c.id == active for c in chats) else MAIN_CHAT)


def _items(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise TypeError
    return [item for item in value if isinstance(item, dict)]


def _dump(chats: ChatList) -> dict[str, object]:
    return {
        "active": chats.active,
        "categories": [{"id": c.id, "name": c.name} for c in chats.categories],
        "chats": [
            {
                "id": c.id,
                "title": c.title,
                "category": c.category,
                "updated_at": c.updated_at.isoformat(),
            }
            for c in chats.chats
        ],
    }


def _erase(store: Path, vault: Path) -> None:
    for suffix in ("", *_SQLITE_SIDECARS):
        store.with_name(store.name + suffix).unlink(missing_ok=True)
    if vault.is_dir():
        shutil.rmtree(vault)
