"""Редактор памяти (S-16.2): правка и удаление фактов из UI; заметки по-прежнему источник истины."""

from collections.abc import Callable
from dataclasses import dataclass

from vtuber.application.memory.privacy import MemoryEraser
from vtuber.application.memory.vault_sync import reconcile
from vtuber.domain import Fact
from vtuber.ports import EmbedderPort, MemoryStorePort, MemoryVaultPort


class MemoryEditor:
    """После правки индекс сверяется сразу: удалённый факт не должен попасть в следующий ответ."""

    def __init__(
        self, vault: MemoryVaultPort, store: MemoryStorePort, embedder: EmbedderPort
    ) -> None:
        self._vault = vault
        self._store = store
        self._embedder = embedder

    async def facts(self) -> list[Fact]:
        """Все факты заметок, новые сверху: чаще правят только что запомненное."""
        found = await self._vault.facts()
        return sorted(found, key=lambda fact: fact.created_at, reverse=True)

    async def update(self, note: str, text: str) -> None:
        """Новый текст факта.

        Raises:
            ValueError: текст пуст или такой заметки нет.
            MemoryUnavailable: папка или индекс недоступны.

        """
        await self._vault.update_fact(note, text)
        await self._sync()

    async def delete(self, note: str) -> None:
        """Факт удаляется из заметок и индекса.

        Raises:
            ValueError: такой заметки нет.
            MemoryUnavailable: папка или индекс недоступны.

        """
        await self._vault.delete_fact(note)
        await self._sync()

    async def _sync(self) -> None:
        await reconcile(self._vault, self._store, self._embedder)


@dataclass(frozen=True, slots=True)
class MemoryControls:
    """Что UI может делать с памятью."""

    editor: MemoryEditor
    eraser: MemoryEraser
    is_working: Callable[[], bool]
