"""Адаптеры портов памяти для контрактных тестов: рабочий и недоступный вариант каждого."""

import tempfile
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.fakes import FakeEmbedder, FakeMemoryStore
from vtuber.adapters.memory import E5Config, E5Embedder, SqliteVecStore
from vtuber.ports import EmbedderPort, MemoryStorePort

ROOT = Path(__file__).resolve().parents[2]
E5_DIR = ROOT / "models" / "memory" / "e5-small"
E5_DIMENSIONS = 384

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


def e5_config(model_dir: Path) -> E5Config:
    """Конфиг e5 для тестов: модель из `models/`, 2 потока, короткий вход."""
    return E5Config(
        model_dir=model_dir, dimensions=E5_DIMENSIONS, threads=2, max_tokens=128, batch_size=8
    )


@asynccontextmanager
async def _sqlite(dims: int) -> AsyncIterator[MemoryStorePort]:
    with tempfile.TemporaryDirectory() as tmp:
        async with SqliteVecStore(Path(tmp) / "memory.sqlite", dims) as store:
            yield store


@asynccontextmanager
async def _sqlite_without_dir(dims: int) -> AsyncIterator[MemoryStorePort]:
    with tempfile.TemporaryDirectory() as tmp:
        # Каталога базы нет — SQLite не откроет файл.
        async with SqliteVecStore(Path(tmp) / "нет" / "memory.sqlite", dims) as store:
            yield store


def embedder_cases() -> list[EmbedderCase]:
    """Все адаптеры EmbedderPort; новый — одна запись здесь."""
    return [
        EmbedderCase(
            name="fake",
            available=lambda: nullcontext(FakeEmbedder()),
            unavailable=lambda: nullcontext(FakeEmbedder(available=False)),
        ),
        EmbedderCase(
            name="e5",
            available=lambda: E5Embedder(e5_config(E5_DIR)),
            unavailable=lambda: E5Embedder(e5_config(E5_DIR / "нет")),
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
        StoreCase(name="sqlite-vec", available=_sqlite, unavailable=_sqlite_without_dir),
    ]


def embedder_params() -> list[object]:
    """Случаи для `pytest`: e5 — медленный (грузит модель) и требует её файлы (ADR-0015)."""
    no_e5 = pytest.mark.skipif(
        not (E5_DIR / "model.onnx").is_file(), reason=f"нет модели e5 в {E5_DIR} (ADR-0015)"
    )
    marks = {"e5": [pytest.mark.slow, no_e5]}
    return [
        pytest.param(case, id=case.name, marks=marks.get(case.name, ()))
        for case in embedder_cases()
    ]


def store_params() -> list[object]:
    """Случаи для `pytest`."""
    return [pytest.param(case, id=case.name) for case in store_cases()]
