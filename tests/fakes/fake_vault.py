"""FakeVault: заметки в памяти (R-56)."""

from dataclasses import dataclass, field, replace
from datetime import datetime

from vtuber.domain import Fact, MemoryUnavailable, Turn


@dataclass(slots=True)
class FakeVault:
    """Реализует MemoryVaultPort; `available=False` — папка недоступна."""

    available: bool = True
    notes: list[Fact] = field(default_factory=list)
    turns: list[Turn] = field(default_factory=list)
    stored_summary: str | None = None

    async def save_fact(self, fact: Fact) -> Fact:
        self._check()
        saved = replace(fact, note=f"заметка {len(self.notes) + 1}")
        self.notes.append(saved)
        return saved

    async def facts(self) -> list[Fact]:
        self._check()
        return list(self.notes)

    async def save_turn(self, turn: Turn, when: datetime) -> None:
        self._check()
        self.turns.append(turn)

    async def recent_turns(self, limit: int) -> list[Turn]:
        self._check()
        return self.turns[-limit:] if limit else []

    async def save_summary(self, summary: str) -> None:
        self._check()
        self.stored_summary = summary

    async def summary(self) -> str | None:
        self._check()
        return self.stored_summary

    def _check(self) -> None:
        if not self.available:
            msg = "FakeVault: папка недоступна (сценарий теста)"
            raise MemoryUnavailable(msg)
