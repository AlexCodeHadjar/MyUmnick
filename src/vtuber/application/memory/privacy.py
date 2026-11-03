"""Очистка всей памяти (S-17.2): заметки, индекс и история; подтверждение спрашивает шлюз."""

from collections.abc import Awaitable, Callable

from vtuber.application.memory.short_term import ShortTermMemory
from vtuber.kernel import get_logger
from vtuber.ports import MemoryStorePort, MemoryVaultPort

_log = get_logger(__name__)


class MemoryEraser:
    """Сначала останавливает всё, что ещё может записать, и лишь потом удаляет.

    Иначе факт, который ждёт простоя, или ход в очереди записи появились бы уже после очистки.
    """

    def __init__(
        self,
        vault: MemoryVaultPort,
        store: MemoryStorePort,
        history: ShortTermMemory,
        quiet: Callable[[], Awaitable[None]],
    ) -> None:
        self._vault = vault
        self._store = store
        self._history = history
        self._quiet = quiet

    async def erase(self) -> None:
        """Удаляет всё.

        Raises:
            MemoryUnavailable: папка или индекс недоступны; часть данных могла остаться.

        """
        await self._quiet()
        self._history.clear()
        await self._vault.erase()
        indexed = await self._store.all_facts()
        for note in {fact.note for fact in indexed}:
            await self._store.remove_note(note)
        _log.info("memory.erased")
