"""Хранилище заметок — источник истины, индекс — производная от него (ADR-0020)."""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Final

from vtuber.domain import Fact, FactHit, FactId, MemoryUnavailable, TurnRemembered, Vector
from vtuber.domain.memory import EmbedKind
from vtuber.kernel import EventBus, get_logger
from vtuber.ports import EmbedderPort, MemoryStorePort, MemoryVaultPort

_STOP: Final = None

_log = get_logger(__name__)


class VaultedFacts:
    """`MemoryStorePort`: сначала заметка, потом индекс; сбой записи не оставит факт без файла."""

    def __init__(self, store: MemoryStorePort, vault: MemoryVaultPort) -> None:
        self._store = store
        self._vault = vault

    async def add(self, fact: Fact, vector: Vector) -> FactId:
        """Заметка, затем вектор в индекс."""
        saved = await self._vault.save_fact(fact)
        return await self._store.add(saved, vector)

    async def search(self, query: Vector, limit: int) -> list[FactHit]:
        """Поиск только по индексу: горячий путь файлы не читает."""
        return await self._store.search(query, limit)

    async def all_facts(self) -> list[Fact]:
        """Факты индекса."""
        return await self._store.all_facts()

    async def clear(self) -> None:
        """Очищает только индекс: заметки — источник истины и не трогаются."""
        await self._store.clear()


async def reconcile(vault: MemoryVaultPort, store: MemoryStorePort, embedder: EmbedderPort) -> int:
    """Приводит индекс к заметкам; старые факты из индекса сначала переносятся в заметки.

    Returns:
        Сколько фактов переиндексировано; 0 — индекс и так совпадал.

    """
    notes = await vault.facts()
    indexed = await store.all_facts()
    if not notes and indexed:
        # База от версии без заметок: это единственный случай, когда индекс знает больше файлов.
        notes = [await vault.save_fact(fact) for fact in indexed]
        _log.info("vault.imported", facts=len(notes))
    if {(f.note, f.text) for f in notes} == {(f.note, f.text) for f in indexed}:
        return 0
    await store.clear()
    vectors = await embedder.embed([fact.text for fact in notes], EmbedKind.PASSAGE)
    for fact, vector in zip(notes, vectors, strict=True):
        await store.add(fact, vector)
    _log.info("vault.reindexed", facts=len(notes))
    return len(notes)


class ChatRecorder:
    """Пишет ходы в заметки своей задачей: подписчик шины только кладёт ход в очередь."""

    def __init__(
        self, vault: MemoryVaultPort, now: Callable[[], datetime] = lambda: datetime.now(UTC)
    ) -> None:
        self._vault = vault
        self._now = now
        self._pending: asyncio.Queue[TurnRemembered | None] = asyncio.Queue()

    def follow(self, bus: EventBus) -> None:
        """Подписка на записанные ходы."""
        bus.subscribe(TurnRemembered, self._on_turn)

    async def _on_turn(self, event: TurnRemembered) -> None:
        self._pending.put_nowait(event)

    def stop(self) -> None:
        """Дописать очередь и завершить `run`: последний ход перед выходом не должен пропасть."""
        self._pending.put_nowait(_STOP)

    async def run(self) -> None:
        """Записывает ходы, пока не вызовут `stop`; сбой диска — потеря записи, а не хода."""
        while (event := await self._pending.get()) is not _STOP:
            try:
                await self._vault.save_turn(event.turn, self._now())
            except MemoryUnavailable as exc:
                _log.warning("vault.turn_not_saved", problem=str(exc))
