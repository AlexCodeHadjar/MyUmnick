"""Хранилище заметок — источник истины, индекс — производная от него (ADR-0020)."""

import asyncio
import time
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime
from typing import Final

from vtuber.application.scheduler import IdleJob
from vtuber.domain import (
    Fact,
    FactHit,
    FactId,
    MemoryUnavailable,
    TurnCancelled,
    TurnFinished,
    TurnRemembered,
    TurnStarted,
    Vector,
)
from vtuber.domain.memory import EmbedKind
from vtuber.kernel import EventBus, get_logger
from vtuber.ports import EmbedderPort, MemoryStorePort, MemoryVaultPort

_STOP: Final = None
MAX_POLL_SHARE: Final = 20

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

    async def remove_note(self, note: str) -> None:
        """Только из индекса: заметку удаляет сам пользователь."""
        await self._store.remove_note(note)


async def reconcile(vault: MemoryVaultPort, store: MemoryStorePort, embedder: EmbedderPort) -> int:
    """Приводит индекс к заметкам: правка главнее индекса, а заметка без разбора его не трогает.

    Сначала векторы, потом изменения: без модели e5 индекс останется прежним, а не опустеет.

    Returns:
        Сколько заметок изменено в индексе; 0 — он и так совпадал.

    """
    scan = await vault.scan()
    indexed = await store.all_facts()
    imported = await _import_old_facts(vault, indexed)
    notes = {*scan.facts, *imported}
    have = set(indexed)
    additions = sorted(notes - have, key=lambda fact: fact.note)
    stale = {fact.note for fact in have - notes} - set(scan.broken)
    vectors = await embedder.embed([fact.text for fact in additions], EmbedKind.PASSAGE)
    for note in stale:
        await store.remove_note(note)
    for fact, vector in zip(additions, vectors, strict=True):
        await store.add(fact, vector)
    changed = {fact.note for fact in additions} | stale
    if changed:
        _log.info("vault.reindexed", notes=len(changed))
    return len(changed - {""})


async def _import_old_facts(vault: MemoryVaultPort, indexed: Sequence[Fact]) -> list[Fact]:
    """Факт без имени заметки — от версии без заметок; потом удалённые пользователем не вернутся."""
    return [await vault.save_fact(fact) for fact in indexed if not fact.note]


class VaultWatcher:
    """Замечает правки опросом: `watchdog` был бы новой зависимостью, а опрос стоит мало (замер).

    Сама сверка — задача простоя: она читает заметки и считает векторы, ходу это мешать не должно.
    """

    def __init__(
        self,
        vault: MemoryVaultPort,
        submit: Callable[[IdleJob], None],
        sync: Callable[[], Awaitable[None]],
        poll_s: float,
    ) -> None:
        self._vault = vault
        self._submit = submit
        self._sync = sync
        self._poll_s = poll_s
        self._waiting = False
        self._idle = asyncio.Event()
        self._idle.set()
        self._last_cost_s = 0.0

    def follow(self, bus: EventBus) -> None:
        """Во время хода папка не опрашивается: на 10 000 заметок опрос заметен циклу событий."""
        bus.subscribe(TurnStarted, self._on_started)
        bus.subscribe(TurnFinished, self._on_ended)
        bus.subscribe(TurnCancelled, self._on_ended)

    async def _on_started(self, _: TurnStarted) -> None:
        self._idle.clear()

    async def _on_ended(self, _: TurnFinished | TurnCancelled) -> None:
        self._idle.set()

    async def run(self) -> None:
        """Следит, пока задачу не отменят; папка пропала — ждёт её возвращения."""
        token = await self._token()
        while True:
            # Большая папка опрашивается реже: не больше примерно 5 % времени на stat.
            await asyncio.sleep(max(self._poll_s, self._last_cost_s * MAX_POLL_SHARE))
            await self._idle.wait()
            current = await self._token()
            if current is None or current == token:
                continue
            token = current
            if not self._waiting:
                self._waiting = True
                self._submit(IdleJob("vault:sync", self._run_sync))

    async def _token(self) -> str | None:
        started = time.monotonic()
        try:
            token = await self._vault.changes_token()
        except MemoryUnavailable as exc:
            _log.warning("vault.unavailable", problem=str(exc))
            return None
        self._last_cost_s = time.monotonic() - started
        return token

    async def _run_sync(self) -> None:
        try:
            await self._sync()
        except Exception:
            self._waiting = False
            raise
        # Отмена ходом сюда не доходит: планировщик повторит задачу, и новая не нужна.
        self._waiting = False


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
