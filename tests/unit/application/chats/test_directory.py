"""Каталог чатов (Этап 21): создание, названия, категории, удаление, файл каталога."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from vtuber.adapters.chats import JsonChatCatalog
from vtuber.application.chats import ChatDirectory
from vtuber.domain import MAIN_CHAT, ChatInfo, ChatList, Turn, TurnId, TurnRemembered, chat_title
from vtuber.kernel import EventBus

WHEN = datetime(2026, 11, 10, tzinfo=UTC)


class _Catalog:
    """Порт в памяти: запоминает сохранения и стёртые чаты."""

    def __init__(self) -> None:
        self.saved: list[ChatList] = []
        self.erased: list[str] = []

    async def load(self) -> ChatList:
        return ChatList((ChatInfo(MAIN_CHAT, "", None, WHEN),), ())

    async def save(self, chats: ChatList) -> None:
        self.saved.append(chats)

    async def erase(self, chat_id: str) -> None:
        self.erased.append(chat_id)


async def _directory() -> tuple[ChatDirectory, _Catalog]:
    catalog = _Catalog()
    return ChatDirectory(catalog, await catalog.load(), clock=lambda: WHEN), catalog


async def test_new_chat_is_listed_and_saved() -> None:
    directory, catalog = await _directory()

    chat_id = await directory.create(None)

    assert directory.chats.chat(chat_id) is not None
    assert directory.chats.active == MAIN_CHAT
    assert catalog.saved[-1] == directory.chats


async def test_first_reply_names_the_open_chat() -> None:
    directory, _ = await _directory()
    bus = EventBus()
    directory.follow(bus)
    turn = Turn(TurnId(1), "Расскажи про кошек и собак", "<happy>Ок")

    await bus.publish(TurnRemembered(turn, ()))
    await bus.publish(TurnRemembered(Turn(TurnId(2), "Другое", "Ок"), ()))

    chat = directory.chats.chat(MAIN_CHAT)
    assert chat is not None
    assert chat.title == "Расскажи про кошек и собак"


async def test_categories_hold_chats_and_deleting_one_keeps_its_chats() -> None:
    directory, _ = await _directory()
    games = await directory.add_category("  Игры  ")
    chat_id = await directory.create(games)

    await directory.rename_category(games, "Игры и аниме")
    assert directory.chats.categories[0].name == "Игры и аниме"
    await directory.remove_category(games)

    chat = directory.chats.chat(chat_id)
    assert chat is not None
    assert chat.category is None
    assert directory.chats.categories == ()


async def test_open_and_main_chat_cannot_be_deleted_other_is_erased() -> None:
    directory, catalog = await _directory()
    other = await directory.create(None)

    with pytest.raises(ValueError, match="нельзя"):
        await directory.remove(MAIN_CHAT)
    await directory.remove(other)

    assert catalog.erased == [other]
    assert directory.chats.chat(other) is None


async def test_unknown_ids_are_errors() -> None:
    directory, _ = await _directory()

    with pytest.raises(ValueError, match="чата"):
        await directory.rename("nope", "x")
    with pytest.raises(ValueError, match="категории"):
        await directory.create("nope")
    with pytest.raises(ValueError, match="пустое"):
        await directory.add_category("   ")


def test_long_title_is_clipped() -> None:
    assert len(chat_title("слово " * 40)) == 60


async def test_json_catalog_round_trip_and_erase(tmp_path: Path) -> None:
    store, vault = tmp_path / "memory-chat-ab.sqlite", tmp_path / "vault" / "chat-ab"
    vault.mkdir(parents=True)
    (vault / "note.md").write_text("x", encoding="utf-8")
    store.write_text("db", encoding="utf-8")
    catalog = JsonChatCatalog(tmp_path / "chats.json", lambda _: (store, vault))
    directory = ChatDirectory(catalog, await catalog.load(), clock=lambda: WHEN)
    games = await directory.add_category("Игры")
    chat_id = await directory.create(games)

    loaded = await JsonChatCatalog(tmp_path / "chats.json", lambda _: (store, vault)).load()
    await catalog.erase(chat_id)
    await catalog.erase(MAIN_CHAT)
    await catalog.erase("../evil")

    assert loaded == directory.chats
    assert not store.exists()
    assert not vault.exists()


async def test_broken_catalog_file_gives_main_chat(tmp_path: Path) -> None:
    path = tmp_path / "chats.json"
    path.write_text("{not json", encoding="utf-8")

    chats = await JsonChatCatalog(path, lambda _: (tmp_path / "a", tmp_path / "b")).load()

    assert [chat.id for chat in chats.chats] == [MAIN_CHAT]
