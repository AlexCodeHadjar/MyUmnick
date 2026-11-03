"""Заметки как источник истины: настоящая папка и SQLite, пересборка индекса из файлов (S-16.4)."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.fakes import FakeEmbedder, FakeMemoryStore
from tests.fakes.fake_vault import FakeVault
from vtuber.adapters.memory import ObsidianVault, SqliteVecStore
from vtuber.application.memory import ChatRecorder, VaultedFacts, reconcile
from vtuber.domain import (
    EmbedKind,
    Fact,
    FactSource,
    MemoryUnavailable,
    Turn,
    TurnId,
    TurnRemembered,
)
from vtuber.kernel import EventBus

WHEN = datetime(2026, 11, 3, 14, 5, tzinfo=UTC)
DIMS = 64


def _fact(text: str) -> Fact:
    return Fact(text, FactSource.EXTRACTED, 0.7, WHEN)


async def _found(store: SqliteVecStore, embedder: FakeEmbedder, text: str) -> str:
    query = (await embedder.embed([text], EmbedKind.QUERY))[0]
    hits = await store.search(query, 1)
    return hits[0].fact.text


async def _remember(vault: ObsidianVault, base: Path, text: str) -> None:
    embedder = FakeEmbedder(DIMS)
    async with SqliteVecStore(base, DIMS) as store:
        vector = (await embedder.embed([text], EmbedKind.PASSAGE))[0]
        await VaultedFacts(store, vault).add(_fact(text), vector)


async def test_deleted_index_is_rebuilt_from_notes(tmp_path: Path) -> None:
    vault = ObsidianVault(tmp_path / "vault")
    base = tmp_path / "index.sqlite"
    await _remember(vault, base, "Живёт в Казани")
    base.unlink()

    embedder = FakeEmbedder(DIMS)
    async with SqliteVecStore(base, DIMS) as store:
        assert await reconcile(vault, store, embedder) == 1
        assert await _found(store, embedder, "Живёт в Казани") == "Живёт в Казани"
        assert await reconcile(vault, store, embedder) == 0  # второй запуск ничего не трогает


async def test_facts_of_old_version_move_to_notes(tmp_path: Path) -> None:
    vault = ObsidianVault(tmp_path / "vault")
    embedder = FakeEmbedder(DIMS)
    async with SqliteVecStore(tmp_path / "old.sqlite", DIMS) as store:
        vector = (await embedder.embed(["Любит котов"], EmbedKind.PASSAGE))[0]
        await store.add(_fact("Любит котов"), vector)
        assert await reconcile(vault, store, embedder) == 1
        notes = await vault.facts()
        assert [f.text for f in notes] == ["Любит котов"]
        assert (await store.all_facts())[0].note == notes[0].note


async def test_index_with_old_schema_opens_and_is_migrated(tmp_path: Path) -> None:
    import sqlite3  # noqa: PLC0415 — создать базу прошлой версии нужно только здесь

    base = tmp_path / "old.sqlite"
    db = sqlite3.connect(base)
    db.execute(
        "create table facts (id integer primary key, text text not null, source text not null,"
        " importance real not null, created_at text not null)"
    )
    db.commit()
    db.close()
    async with SqliteVecStore(base, DIMS) as store:
        assert await store.all_facts() == []


def test_note_opens_as_obsidian_markdown(tmp_path: Path) -> None:
    async def write() -> None:
        await ObsidianVault(tmp_path).save_fact(_fact("Живёт в Казани"))

    asyncio.run(write())
    note = next((tmp_path / "Факты").glob("*.md"))
    text = note.read_text(encoding="utf-8")
    assert text.startswith("---\nsource: extracted\n")
    assert "[[Люди/Ведущий]]" in text
    assert "[[Дневник/2026-11-03]]" in text
    assert (tmp_path / "Люди" / "Ведущий.md").is_file()
    assert note.stem in (tmp_path / "Дневник" / "2026-11-03.md").read_text(encoding="utf-8")


def test_user_text_that_looks_like_markup_survives(tmp_path: Path) -> None:
    tricky = "## 10:00:00\n**Ты:** подделка\n\\обратная черта\n**Витюбер:** тоже"

    async def scenario() -> list[Turn]:
        vault = ObsidianVault(tmp_path)
        await vault.save_turn(Turn(TurnId(1), tricky, tricky), WHEN)
        await vault.save_turn(Turn(TurnId(2), "после", "ответ"), WHEN)
        return await vault.recent_turns(5)

    first, second = asyncio.run(scenario())
    assert first.user_text == tricky
    assert first.reply_text == tricky
    assert second.user_text == "после"


def test_broken_note_does_not_break_the_rest(tmp_path: Path) -> None:
    async def scenario() -> list[Fact]:
        vault = ObsidianVault(tmp_path)
        await vault.save_fact(_fact("Целый факт"))
        (tmp_path / "Факты" / "битая.md").write_text("просто текст", encoding="utf-8")
        return await vault.facts()

    assert [f.text for f in asyncio.run(scenario())] == ["Целый факт"]


def test_note_edited_by_hand_with_other_quotes_is_read(tmp_path: Path) -> None:
    async def scenario() -> list[Fact]:
        folder = tmp_path / "Факты"
        folder.mkdir()
        (folder / "своя.md").write_text(
            "---\nsource: user\nimportance: 1\ncreated: 2026-11-03T14:05:00+00:00\n"
            "aliases: [x]\n---\n\nЛюбит чай\r\n",
            encoding="utf-8",
        )
        return await ObsidianVault(tmp_path).facts()

    (fact,) = asyncio.run(scenario())
    assert fact.text == "Любит чай"
    assert fact.note == "своя"
    assert fact.source is FactSource.USER


async def test_recorder_writes_turns_and_flushes_on_stop() -> None:
    bus = EventBus()
    vault = FakeVault()
    recorder = ChatRecorder(vault)
    recorder.follow(bus)
    running = asyncio.create_task(recorder.run())
    await bus.publish(TurnRemembered(Turn(TurnId(1), "а", "б"), ()))
    recorder.stop()
    await asyncio.wait_for(running, 1)
    assert [t.user_text for t in vault.turns] == ["а"]


async def test_recorder_survives_a_broken_disk() -> None:
    bus = EventBus()
    recorder = ChatRecorder(FakeVault(available=False))
    recorder.follow(bus)
    running = asyncio.create_task(recorder.run())
    await bus.publish(TurnRemembered(Turn(TurnId(1), "а", "б"), ()))
    recorder.stop()
    await asyncio.wait_for(running, 1)


async def test_fact_without_a_note_never_reaches_the_index() -> None:
    store = FakeMemoryStore(dimensions=DIMS)
    facts = VaultedFacts(store, FakeVault(available=False))
    vector = (await FakeEmbedder(DIMS).embed(["x"], EmbedKind.PASSAGE))[0]
    with pytest.raises(MemoryUnavailable):
        await facts.add(_fact("x"), vector)
    assert store.facts == []


def test_erase_keeps_the_users_other_notes(tmp_path: Path) -> None:
    async def scenario() -> None:
        vault = ObsidianVault(tmp_path)
        await vault.save_fact(_fact("факт"))
        (tmp_path / "Мои проекты.md").write_text("чужая заметка", encoding="utf-8")
        await vault.erase()

    asyncio.run(scenario())
    assert (tmp_path / "Мои проекты.md").is_file()
    assert not list((tmp_path / "Факты").glob("*.md"))
