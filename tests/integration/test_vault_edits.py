"""Правки заметок: настоящая папка и SQLite, индекс догоняет без перезапуска (S-16.5)."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.fakes import FakeEmbedder
from tests.fakes.fake_vault import FakeVault
from vtuber.adapters.memory import ObsidianVault, SqliteVecStore
from vtuber.application.memory import VaultWatcher, reconcile
from vtuber.application.scheduler import IdleJob
from vtuber.domain import EmbedKind, Fact, FactSource, TurnFinished, TurnId, TurnStarted
from vtuber.kernel import EventBus

WHEN = datetime(2026, 11, 3, 14, 5, tzinfo=UTC)
DIMS = 64
POLL_S = 0.01


@dataclass(slots=True)
class _Memory:
    vault: ObsidianVault
    store: SqliteVecStore
    embedder: FakeEmbedder
    folder: Path

    async def learn(self, text: str) -> Fact:
        saved = await self.vault.save_fact(Fact(text, FactSource.EXTRACTED, 0.7, WHEN))
        await reconcile(self.vault, self.store, self.embedder)
        return saved

    async def indexed(self) -> list[str]:
        return [fact.text for fact in await self.store.all_facts()]

    async def top(self, text: str) -> str:
        query = (await self.embedder.embed([text], EmbedKind.QUERY))[0]
        return (await self.store.search(query, 1))[0].fact.text

    def path(self, fact: Fact) -> Path:
        return self.folder / "Факты" / f"{fact.note}.md"


@asynccontextmanager
async def _memory(tmp_path: Path) -> AsyncIterator[_Memory]:
    async with SqliteVecStore(tmp_path / "index.sqlite", DIMS) as store:
        vault = ObsidianVault(tmp_path / "vault")
        yield _Memory(vault, store, FakeEmbedder(DIMS), tmp_path / "vault")


async def test_edited_note_changes_what_search_finds(tmp_path: Path) -> None:
    async with _memory(tmp_path) as memory:
        fact = await memory.learn("Живёт в Казани")
        path = memory.path(fact)
        path.write_text(
            path.read_text(encoding="utf-8").replace("Казани", "Москве"), encoding="utf-8"
        )

        assert await reconcile(memory.vault, memory.store, memory.embedder) == 1
        assert await memory.indexed() == ["Живёт в Москве"]
        assert await memory.top("Живёт в Москве") == "Живёт в Москве"


async def test_deleted_note_is_no_longer_found(tmp_path: Path) -> None:
    async with _memory(tmp_path) as memory:
        gone = await memory.learn("Любит котов")
        await memory.learn("Живёт в Казани")
        memory.path(gone).unlink()

        await reconcile(memory.vault, memory.store, memory.embedder)
        assert await memory.indexed() == ["Живёт в Казани"]


async def test_user_deleting_every_note_does_not_bring_facts_back(tmp_path: Path) -> None:
    async with _memory(tmp_path) as memory:
        fact = await memory.learn("Любит котов")
        memory.path(fact).unlink()

        await reconcile(memory.vault, memory.store, memory.embedder)
        assert await memory.indexed() == []
        assert await memory.vault.facts() == []


async def test_new_note_written_by_user_gets_into_the_index(tmp_path: Path) -> None:
    async with _memory(tmp_path) as memory:
        await memory.learn("Живёт в Казани")
        (memory.folder / "Факты" / "моя.md").write_text(
            "---\nsource: user\nimportance: 1\ncreated: 2026-11-03T15:00:00+00:00\n---\n"
            "Любит чай\n",
            encoding="utf-8",
        )

        await reconcile(memory.vault, memory.store, memory.embedder)
        assert sorted(await memory.indexed()) == ["Живёт в Казани", "Любит чай"]


async def test_note_broken_by_an_edit_keeps_its_fact_until_fixed(tmp_path: Path) -> None:
    async with _memory(tmp_path) as memory:
        fact = await memory.learn("Живёт в Казани")
        good = memory.path(fact).read_text(encoding="utf-8")
        memory.path(fact).write_text("---\nне закрыт блок", encoding="utf-8")

        await reconcile(memory.vault, memory.store, memory.embedder)
        assert await memory.indexed() == ["Живёт в Казани"]

        memory.path(fact).write_text(good.replace("Казани", "Твери"), encoding="utf-8")
        await reconcile(memory.vault, memory.store, memory.embedder)
        assert await memory.indexed() == ["Живёт в Твери"]


async def test_vtuber_does_not_overwrite_note_edited_by_user(tmp_path: Path) -> None:
    async with _memory(tmp_path) as memory:
        fact = Fact("Живёт в Казани", FactSource.EXTRACTED, 0.7, WHEN)
        saved = await memory.vault.save_fact(fact)
        edited = memory.path(saved).read_text(encoding="utf-8").replace("Казани", "Москве")
        memory.path(saved).write_text(edited, encoding="utf-8")

        await memory.vault.save_fact(fact)

        assert memory.path(saved).read_text(encoding="utf-8") == edited


async def test_many_concurrent_writes_lose_nothing(tmp_path: Path) -> None:
    async with _memory(tmp_path) as memory:
        facts = [Fact(f"факт {i}", FactSource.EXTRACTED, 0.5, WHEN) for i in range(30)]
        await asyncio.gather(*(memory.vault.save_fact(fact) for fact in facts))
        assert len(await memory.vault.facts()) == 30
        diary = (memory.folder / "Дневник" / "2026-11-03.md").read_text(encoding="utf-8")
        assert len(diary.splitlines()) == 30


async def test_token_changes_when_a_note_changes(tmp_path: Path) -> None:
    async with _memory(tmp_path) as memory:
        empty = await memory.vault.changes_token()
        fact = await memory.learn("Живёт в Казани")
        learned = await memory.vault.changes_token()
        assert learned != empty
        assert await memory.vault.changes_token() == learned
        memory.path(fact).unlink()
        assert await memory.vault.changes_token() != learned


class _Jobs:
    def __init__(self) -> None:
        self.submitted: list[IdleJob] = []

    def submit(self, job: IdleJob) -> None:
        self.submitted.append(job)


async def _settle() -> None:
    await asyncio.sleep(POLL_S * 5)


async def test_watcher_syncs_once_per_change_through_idle_jobs() -> None:
    vault = FakeVault()
    jobs = _Jobs()
    synced: list[int] = []

    async def sync() -> None:
        synced.append(1)

    watcher = VaultWatcher(vault, jobs.submit, sync, POLL_S)
    running = asyncio.create_task(watcher.run())
    await _settle()
    assert jobs.submitted == []  # начальное состояние — не изменение

    await vault.save_fact(Fact("а", FactSource.USER, 0.5, WHEN))
    await _settle()
    await vault.save_fact(Fact("б", FactSource.USER, 0.5, WHEN))
    await _settle()
    assert len(jobs.submitted) == 1  # задача ещё ждёт простоя: вторая не нужна

    await jobs.submitted[0].run()
    assert synced == [1]
    await vault.save_fact(Fact("в", FactSource.USER, 0.5, WHEN))
    await _settle()
    assert len(jobs.submitted) == 2
    running.cancel()


async def test_watcher_survives_an_unavailable_folder() -> None:
    vault = FakeVault(available=False)
    jobs = _Jobs()

    async def sync() -> None:
        await asyncio.sleep(0)

    running = asyncio.create_task(VaultWatcher(vault, jobs.submit, sync, POLL_S).run())
    await _settle()
    assert not running.done()
    vault.available = True
    await vault.save_fact(Fact("а", FactSource.USER, 0.5, WHEN))
    await _settle()
    assert len(jobs.submitted) == 1
    running.cancel()


async def test_watcher_does_not_poll_during_a_turn() -> None:
    bus = EventBus()
    vault = FakeVault()
    polls: list[int] = []
    original = vault.changes_token

    class _Counting:
        def __getattr__(self, name: str) -> object:
            return getattr(vault, name)

        async def changes_token(self) -> str:
            polls.append(1)
            return await original()

    async def sync() -> None:
        await asyncio.sleep(0)

    watcher = VaultWatcher(_Counting(), _Jobs().submit, sync, POLL_S)  # type: ignore[arg-type]
    watcher.follow(bus)
    running = asyncio.create_task(watcher.run())
    await _settle()
    await bus.publish(TurnStarted(TurnId(1)))
    await _settle()
    during = len(polls)
    await _settle()
    assert len(polls) <= during + 1
    await bus.publish(TurnFinished(TurnId(1)))
    await _settle()
    assert len(polls) > during + 1
    running.cancel()


async def test_unchanged_notes_are_not_read_again(tmp_path: Path) -> None:
    async with _memory(tmp_path) as memory:
        fact = await memory.learn("Живёт в Казани")
        first = (await memory.vault.scan()).facts
        reads: list[Path] = []
        original = Path.read_text

        def counting(path: Path, *args: str, **kwargs: str) -> str:
            reads.append(path)
            return original(path, *args, **kwargs)

        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(Path, "read_text", counting)
            assert (await memory.vault.scan()).facts == first
            assert reads == []
            path = memory.path(fact)
            original_text = original(path, encoding="utf-8")
            path.write_text(original_text.replace("Казани", "Твери"), encoding="utf-8")
            assert (await memory.vault.scan()).facts[0].text == "Живёт в Твери"
            assert reads == [path]
