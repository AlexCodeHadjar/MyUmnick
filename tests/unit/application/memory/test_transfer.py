"""Перенос фактов между изданиями (S-20.10): выгрузка во входящие, приём, перевод русским ядром."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.fakes import FakeEmbedder, FakeLLM, FakeMemoryStore
from tests.fakes.fake_vault import FakeVault
from vtuber.application.memory import FactTransfer, MemoryParts, TransferPaths, TransferRequests
from vtuber.application.scheduler import IdleScheduler, SchedulerConfig
from vtuber.domain import Fact, FactSource, GenerationFailed
from vtuber.ports import GenerationParams

WHEN = datetime(2026, 11, 10, tzinfo=UTC)
PARAMS = GenerationParams(max_tokens=64, temperature=0.0)


def _paths(tmp_path: Path, own: str, other: str) -> TransferPaths:
    return TransferPaths(
        own_inbox=tmp_path / own / "inbox" / "facts.jsonl",
        other_inbox=tmp_path / other / "inbox" / "facts.jsonl",
        own_language=own,
        other_language=other,
    )


def _memory(vault: FakeVault) -> MemoryParts:
    return MemoryParts(vault, FakeMemoryStore(), FakeEmbedder())


async def test_russian_core_exports_translated_facts_to_english_inbox(tmp_path: Path) -> None:
    vault = FakeVault(notes=[Fact("Пользователя зовут Саша", FactSource.USER, 1.0, WHEN)])
    llm = FakeLLM("The user's name is Sasha\n")
    transfer = FactTransfer(_paths(tmp_path, "ru", "en"), _memory(vault), (llm, PARAMS))

    assert await transfer.export() == 1

    rows = (tmp_path / "en" / "inbox" / "facts.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(rows[0]) == {
        "text": "The user's name is Sasha",
        "importance": 1.0,
        "from": "ru",
    }
    assert "English" in llm.calls[0][0][0].text


async def test_english_core_imports_as_is_and_marks_inbox_done(tmp_path: Path) -> None:
    paths = _paths(tmp_path, "en", "ru")
    paths.own_inbox.parent.mkdir(parents=True)
    paths.own_inbox.write_text(
        '{"text": "The user\'s name is Sasha", "importance": 1.0}\nbroken line\n', encoding="utf-8"
    )
    vault = FakeVault()

    added = await FactTransfer(paths, _memory(vault), None).import_inbox(WHEN)

    assert added == 1
    assert [fact.text for fact in vault.notes] == ["The user's name is Sasha"]
    assert not paths.own_inbox.exists()
    assert paths.own_inbox.with_name("facts.jsonl.done").exists()


async def test_repeated_import_does_not_duplicate_facts(tmp_path: Path) -> None:
    paths = _paths(tmp_path, "en", "ru")
    paths.own_inbox.parent.mkdir(parents=True)
    vault = FakeVault(notes=[Fact("Likes cats", FactSource.USER, 0.5, WHEN)])
    paths.own_inbox.write_text('{"text": "likes cats", "importance": 0.5}\n', encoding="utf-8")

    assert await FactTransfer(paths, _memory(vault), None).import_inbox(WHEN) == 0
    assert len(vault.notes) == 1


async def test_russian_core_translates_english_facts_on_import(tmp_path: Path) -> None:
    paths = _paths(tmp_path, "ru", "en")
    paths.own_inbox.parent.mkdir(parents=True)
    paths.own_inbox.write_text('{"text": "Likes cats", "importance": 0.5}\n', encoding="utf-8")
    vault = FakeVault()

    await FactTransfer(paths, _memory(vault), (FakeLLM("Любит котов"), PARAMS)).import_inbox(WHEN)

    assert [fact.text for fact in vault.notes] == ["Любит котов"]


async def test_wrong_line_count_keeps_inbox_for_next_time(tmp_path: Path) -> None:
    paths = _paths(tmp_path, "ru", "en")
    paths.own_inbox.parent.mkdir(parents=True)
    paths.own_inbox.write_text(
        '{"text": "A", "importance": 0.5}\n{"text": "B", "importance": 0.5}\n', encoding="utf-8"
    )
    transfer = FactTransfer(paths, _memory(FakeVault()), (FakeLLM("только одна строка"), PARAMS))

    with pytest.raises(GenerationFailed):
        await transfer.import_inbox(WHEN)
    assert paths.own_inbox.exists()


async def test_nothing_to_import_is_quiet(tmp_path: Path) -> None:
    transfer = FactTransfer(_paths(tmp_path, "en", "ru"), _memory(FakeVault()), None)

    assert await transfer.import_inbox(WHEN) == 0


async def test_requests_run_export_in_idle_and_report(tmp_path: Path) -> None:
    vault = FakeVault(notes=[Fact("Likes cats", FactSource.USER, 0.5, WHEN)])
    transfer = FactTransfer(_paths(tmp_path, "en", "ru"), _memory(vault), None)
    scheduler = IdleScheduler(SchedulerConfig(idle_after_ms=1))
    results: list[tuple[int | None, str | None]] = []

    async def done(count: int | None, problem: str | None) -> None:
        results.append((count, problem))

    TransferRequests(transfer, scheduler).request(done)
    runner = asyncio.create_task(scheduler.run())
    scheduler.idle()
    for _ in range(300):
        if results:
            break
        await asyncio.sleep(0.01)
    runner.cancel()

    assert results == [(1, None)]
    assert (tmp_path / "ru" / "inbox" / "facts.jsonl").exists()
