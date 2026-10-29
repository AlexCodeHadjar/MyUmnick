"""Порты долговременной памяти: эмбеддер и хранилище — раздельно (ISP).

Эмбеддер меняется вместе с моделью (e5, bge-m3), хранилище — вместе с базой (sqlite-vec);
сервису памяти нужны оба, гейту поиска — только эмбеддер для запроса.
"""

from collections.abc import Sequence
from typing import Protocol

from vtuber.domain import EmbedKind, Fact, FactHit, FactId, Vector


class EmbedderPort(Protocol):
    """Тексты → векторы единичной длины.

    Контракт — `tests/contract/test_embedder_contract.py`: длина и размерность, единичная норма,
    детерминизм, близкое по смыслу ближе далёкого, недоступная модель — `MemoryUnavailable`.
    """

    @property
    def dimensions(self) -> int:
        """Размерность векторов модели: хранилище создаётся под неё."""
        ...

    async def embed(self, texts: Sequence[str], kind: EmbedKind) -> list[Vector]:
        """Вектор на каждый текст по порядку; пустой список — пустой ответ, не ошибка.

        Raises:
            MemoryUnavailable: модель не загружена.

        """
        ...


class MemoryStorePort(Protocol):
    """Факты с векторами: добавить и найти ближайшие.

    Контракт — `tests/contract/test_memory_store_contract.py`: добавленный факт находится своим
    вектором первым, выдача по убыванию близости и не длиннее `limit`, вектор не той
    размерности — `ValueError`, недоступное хранилище — `MemoryUnavailable`.
    """

    async def add(self, fact: Fact, vector: Vector) -> FactId:
        """Запоминает факт с его вектором; id — для правки и удаления (дедупликация, S-10.4).

        Raises:
            ValueError: размерность вектора не та, под которую создано хранилище.
            MemoryUnavailable: хранилище не открыто.

        """
        ...

    async def search(self, query: Vector, limit: int) -> list[FactHit]:
        """До `limit` ближайших к `query` фактов, от самого близкого (T-12: ≤ 40 мс на топ-k).

        Raises:
            ValueError: размерность вектора не та или `limit` < 1.
            MemoryUnavailable: хранилище не открыто.

        """
        ...
