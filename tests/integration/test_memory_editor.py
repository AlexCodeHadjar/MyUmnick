"""Редактор памяти: настоящая папка и SQLite, профили не смешиваются (S-16.2)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.fakes import FakeEmbedder
from vtuber.adapters.memory import ObsidianVault, SqliteVecStore
from vtuber.application.memory import MemoryEditor, reconcile
from vtuber.bootstrap.config import load_app_config
from vtuber.domain import EmbedKind, Fact, FactSource
from vtuber.gateway import MemoryBridge, OutboundMessage
from vtuber.gateway.protocol_memory import (
    FactDeleteData,
    FactSaveData,
    MemoryFactDelete,
    MemoryFacts,
    MemoryFactSave,
)

WHEN = datetime(2026, 11, 3, 14, 5, tzinfo=UTC)
DIMS = 64
ROOT = Path(__file__).resolve().parents[2]


def _make_folder(path: Path) -> None:
    path.mkdir(parents=True)


@asynccontextmanager
async def _editor(
    folder: Path,
) -> AsyncIterator[tuple[MemoryEditor, SqliteVecStore, ObsidianVault]]:
    async with SqliteVecStore(folder / "index.sqlite", DIMS) as store:
        vault = ObsidianVault(folder / "vault")
        yield MemoryEditor(vault, store, FakeEmbedder(DIMS)), store, vault


async def _learn(vault: ObsidianVault, store: SqliteVecStore, text: str, age: int = 0) -> Fact:
    when = WHEN + timedelta(hours=age)
    saved = await vault.save_fact(Fact(text, FactSource.EXTRACTED, 0.7, when))
    await reconcile(vault, store, FakeEmbedder(DIMS))
    return saved


async def _top(store: SqliteVecStore, text: str) -> list[str]:
    query = (await FakeEmbedder(DIMS).embed([text], EmbedKind.QUERY))[0]
    return [hit.fact.text for hit in await store.search(query, 5)]


async def test_edit_takes_effect_on_search_at_once_and_keeps_properties(tmp_path: Path) -> None:
    async with _editor(tmp_path) as (editor, store, vault):
        fact = await _learn(vault, store, "Живёт в Казани")
        await editor.update(fact.note, "Живёт в Москве")
        assert await _top(store, "Живёт в Москве") == ["Живёт в Москве"]
        (edited,) = await editor.facts()
        assert edited.note == fact.note
        assert edited.source is FactSource.EXTRACTED
        assert edited.created_at == fact.created_at


async def test_deleted_fact_is_not_found(tmp_path: Path) -> None:
    async with _editor(tmp_path) as (editor, store, vault):
        gone = await _learn(vault, store, "Любит котов")
        await _learn(vault, store, "Живёт в Казани")
        await editor.delete(gone.note)
        assert await _top(store, "Любит котов") == ["Живёт в Казани"]
        assert [f.text for f in await editor.facts()] == ["Живёт в Казани"]


async def test_newest_comes_first(tmp_path: Path) -> None:
    async with _editor(tmp_path) as (editor, store, vault):
        await _learn(vault, store, "старый", age=0)
        await _learn(vault, store, "новый", age=5)
        assert [f.text for f in await editor.facts()] == ["новый", "старый"]


@pytest.mark.parametrize("note", ["нет такой", "../../секрет", "..\\секрет", "Факты/x", ""])
async def test_unknown_or_escaping_note_is_refused(tmp_path: Path, note: str) -> None:
    secret = tmp_path / "секрет.md"
    secret.write_text("не трогать", encoding="utf-8")
    async with _editor(tmp_path) as (editor, _, _):
        with pytest.raises(ValueError, match="заметк"):
            await editor.delete(note)
        with pytest.raises(ValueError, match="заметк"):
            await editor.update(note, "текст")
    assert secret.read_text(encoding="utf-8") == "не трогать"


async def test_empty_text_is_refused(tmp_path: Path) -> None:
    async with _editor(tmp_path) as (editor, store, vault):
        fact = await _learn(vault, store, "Живёт в Казани")
        with pytest.raises(ValueError, match="пуст"):
            await editor.update(fact.note, "   ")
        assert [f.text for f in await editor.facts()] == ["Живёт в Казани"]


async def test_profiles_do_not_mix(tmp_path: Path) -> None:
    env = {
        "VTUBER_MEMORY__PROFILE": "Аня",
        "VTUBER_MEMORY__VAULT_PATH": "vault",
        "VTUBER_MEMORY__STORE_PATH": "base/index.sqlite",
    }
    anya = load_app_config(ROOT, env).memory.resolved(tmp_path)
    boris = load_app_config(ROOT, {**env, "VTUBER_MEMORY__PROFILE": "Боря"}).memory.resolved(
        tmp_path
    )
    shared = load_app_config(ROOT, {**env, "VTUBER_MEMORY__PROFILE": ""}).memory.resolved(tmp_path)

    assert anya.vault_path != boris.vault_path
    assert anya.store_path != boris.store_path
    # Без профиля пути прежние: данные старой версии остаются на месте.
    assert shared.vault_path == tmp_path / "vault"
    assert shared.store_path == tmp_path / "base" / "index.sqlite"

    _make_folder(anya.store_path.parent)
    async with (
        SqliteVecStore(anya.store_path, DIMS) as first,
        SqliteVecStore(boris.store_path, DIMS) as second,
    ):
        await _learn(ObsidianVault(anya.vault_path), first, "Факт Ани")
        await _learn(ObsidianVault(boris.vault_path), second, "Факт Бори")
        assert await _top(first, "Факт Бори") == ["Факт Ани"]
        assert await _top(second, "Факт Ани") == ["Факт Бори"]


@pytest.mark.parametrize("name", ["../чужой", "a/b", "..", "a\\b"])
def test_profile_cannot_leave_the_folder(name: str) -> None:
    env = {"VTUBER_MEMORY__PROFILE": name}
    with pytest.raises(ValueError, match="профил"):
        load_app_config(ROOT, env).memory.resolved(Path("корень"))


async def test_bridge_answers_with_fresh_list_and_shows_problem(tmp_path: Path) -> None:
    sent: list[OutboundMessage] = []

    async def send(message: OutboundMessage) -> None:
        sent.append(message)

    async with _editor(tmp_path) as (editor, store, vault):
        fact = await _learn(vault, store, "Живёт в Казани")
        bridge = MemoryBridge(editor, send)
        save = FactSaveData(note=fact.note, text="Живёт в Туле")
        await bridge.handle(MemoryFactSave(v=1, type="memory.fact_save", data=save))
        wrong = FactDeleteData(note="нет такой")
        await bridge.handle(MemoryFactDelete(v=1, type="memory.fact_delete", data=wrong))

    first, second = sent
    assert isinstance(first, MemoryFacts)
    assert isinstance(second, MemoryFacts)
    assert first.data.facts[0].text == "Живёт в Туле"
    assert first.data.problem is None
    assert second.data.problem
    assert second.data.facts[0].text == "Живёт в Туле"


async def test_bridge_without_memory_says_so() -> None:
    sent: list[OutboundMessage] = []

    async def send(message: OutboundMessage) -> None:
        sent.append(message)

    data = FactDeleteData(note="x")
    await MemoryBridge(None, send).handle(
        MemoryFactDelete(v=1, type="memory.fact_delete", data=data)
    )
    assert isinstance(sent[0], MemoryFacts)
    assert sent[0].data.problem
