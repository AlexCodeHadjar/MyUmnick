"""Контракт MemoryVaultPort: что записано, то прочитано и после перезапуска."""

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.fakes.fake_vault import FakeVault
from vtuber.adapters.memory import ObsidianVault
from vtuber.domain import Fact, FactSource, Turn, TurnId
from vtuber.ports import MemoryVaultPort

WHEN = datetime(2026, 11, 3, 14, 5, 7, tzinfo=UTC)

type VaultFactory = Callable[[Path], MemoryVaultPort]


@pytest.fixture(params=["fake", "obsidian"])
def vault(request: pytest.FixtureRequest, tmp_path: Path) -> MemoryVaultPort:
    return FakeVault() if request.param == "fake" else ObsidianVault(tmp_path / "хранилище")


def _fact(text: str = "Живёт в Казани") -> Fact:
    return Fact(text, FactSource.EXTRACTED, 0.7, WHEN)


async def test_saved_fact_is_read_back_with_its_note_name(vault: MemoryVaultPort) -> None:
    saved = await vault.save_fact(_fact())
    assert saved.note
    assert await vault.facts() == [saved]


async def test_two_facts_get_different_notes(vault: MemoryVaultPort) -> None:
    first = await vault.save_fact(_fact())
    second = await vault.save_fact(_fact("Любит котов"))
    assert first.note != second.note


async def test_turns_are_read_back_in_order_with_flags(vault: MemoryVaultPort) -> None:
    await vault.save_turn(Turn(TurnId(1), "привет", "<happy>Привет!"), WHEN)
    await vault.save_turn(Turn(TurnId(2), "как дела", "Хор", is_interrupted=True), WHEN)
    await vault.save_turn(Turn(TurnId(3), "зритель", "ответ", is_external=True), WHEN)
    turns = await vault.recent_turns(10)
    assert [t.user_text for t in turns] == ["привет", "как дела", "зритель"]
    assert turns[0].reply_text == "<happy>Привет!"
    assert [t.is_interrupted for t in turns] == [False, True, False]
    assert [t.is_external for t in turns] == [False, False, True]


async def test_recent_turns_keeps_only_the_newest(vault: MemoryVaultPort) -> None:
    for index in range(5):
        await vault.save_turn(Turn(TurnId(index), str(index), "ответ"), WHEN)
    assert [t.user_text for t in await vault.recent_turns(2)] == ["3", "4"]
    assert await vault.recent_turns(0) == []


async def test_summary_is_replaced_and_empty_at_first(vault: MemoryVaultPort) -> None:
    assert await vault.summary() is None
    await vault.save_summary("первое")
    await vault.save_summary("второе")
    assert await vault.summary() == "второе"


async def test_empty_vault_has_nothing(vault: MemoryVaultPort) -> None:
    assert await vault.facts() == []
    assert await vault.recent_turns(5) == []
