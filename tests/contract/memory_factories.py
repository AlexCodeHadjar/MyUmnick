"""Адаптеры портов памяти для контрактных тестов: рабочий и недоступный вариант каждого.

Настоящие адаптеры (e5, sqlite-vec) добавятся здесь в S-10.2 — контракт прогонится на них сам.
"""

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, nullcontext
from dataclasses import dataclass

import pytest

from tests.fakes import FakeEmbedder, FakeMemoryStore
from vtuber.ports import EmbedderPort, MemoryStorePort

type EmbedderFactory = Callable[[], AbstractAsyncContextManager[EmbedderPort]]
type StoreFactory = Callable[[int], AbstractAsyncContextManager[MemoryStorePort]]
"""Хранилище под векторы заданной размерности (её задаёт эмбеддер)."""


@dataclass(frozen=True, slots=True)
class EmbedderCase:
    """Как получить адаптер EmbedderPort: с загруженной моделью и без неё."""

    name: str
    available: EmbedderFactory
    unavailable: EmbedderFactory


@dataclass(frozen=True, slots=True)
class StoreCase:
    """Как получить адаптер MemoryStorePort: открытый и недоступный."""

    name: str
    available: StoreFactory
    unavailable: StoreFactory


def embedder_cases() -> list[EmbedderCase]:
    """Все адаптеры EmbedderPort; новый — одна запись здесь."""
    return [
        EmbedderCase(
            name="fake",
            available=lambda: nullcontext(FakeEmbedder()),
            unavailable=lambda: nullcontext(FakeEmbedder(available=False)),
        ),
    ]


def store_cases() -> list[StoreCase]:
    """Все адаптеры MemoryStorePort; новый — одна запись здесь."""
    return [
        StoreCase(
            name="fake",
            available=lambda dims: nullcontext(FakeMemoryStore(dimensions=dims)),
            unavailable=lambda dims: nullcontext(FakeMemoryStore(dimensions=dims, available=False)),
        ),
    ]


def embedder_params() -> list[object]:
    """Случаи для `pytest`; медленные адаптеры получат метки, как TTS в `factories.py`."""
    return [pytest.param(case, id=case.name) for case in embedder_cases()]


def store_params() -> list[object]:
    """Случаи для `pytest`."""
    return [pytest.param(case, id=case.name) for case in store_cases()]
