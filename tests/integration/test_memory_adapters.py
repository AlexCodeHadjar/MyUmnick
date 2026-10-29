"""Адаптеры памяти сверх контракта: файл базы между запусками и время поиска (S-10.2, ADR-0015)."""

import math
import random
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.contract.memory_factories import E5_DIMENSIONS, E5_DIR, e5_config
from tools.bench_latency import percentile
from vtuber.adapters.memory import E5Embedder, SqliteVecStore
from vtuber.domain import EmbedKind, Fact, FactSource, MemoryUnavailable, Vector

WHEN = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)
# Бюджет «решение о поиске + поиск» (docs/performance.md); замер — только поиск и запрос.
SEARCH_BUDGET_MS = 40.0
FACTS_FOR_TIMING = 2000


def _random_unit(rng: random.Random, dims: int) -> Vector:
    values = [rng.gauss(0, 1) for _ in range(dims)]
    norm = math.sqrt(sum(v * v for v in values))
    return tuple(v / norm for v in values)


async def test_facts_survive_reopening_the_file(tmp_path: Path) -> None:
    path = tmp_path / "memory.sqlite"
    vector = _random_unit(random.Random(1), 8)
    fact = Fact("Любит котов", FactSource.USER, 0.9, WHEN)
    async with SqliteVecStore(path, 8) as store:
        await store.add(fact, vector)

    async with SqliteVecStore(path, 8) as store:
        (hit,) = await store.search(vector, limit=1)

    assert hit.fact == fact


async def test_other_dimensions_on_existing_file_is_unavailable(tmp_path: Path) -> None:
    path = tmp_path / "memory.sqlite"
    async with SqliteVecStore(path, 8) as store:
        await store.add(Fact("x", FactSource.USER, 0.5, WHEN), _random_unit(random.Random(2), 8))

    async with SqliteVecStore(path, 16) as store:
        with pytest.raises(MemoryUnavailable, match="переиндексация"):
            await store.search(_random_unit(random.Random(3), 16), limit=1)


@pytest.mark.slow
async def test_top_k_search_fits_budget(tmp_path: Path) -> None:
    rng = random.Random(4)
    async with SqliteVecStore(tmp_path / "memory.sqlite", E5_DIMENSIONS) as store:
        for i in range(FACTS_FOR_TIMING):
            fact = Fact(f"факт {i}", FactSource.EXTRACTED, 0.5, WHEN)
            await store.add(fact, _random_unit(rng, E5_DIMENSIONS))
        timings = []
        for _ in range(50):
            query = _random_unit(rng, E5_DIMENSIONS)
            started = time.perf_counter()
            await store.search(query, limit=5)
            timings.append((time.perf_counter() - started) * 1000)

    assert percentile(timings, 0.95) <= SEARCH_BUDGET_MS


@pytest.mark.slow
@pytest.mark.skipif(not (E5_DIR / "model.onnx").is_file(), reason=f"нет модели e5 в {E5_DIR}")
async def test_query_embedding_plus_search_fits_budget(tmp_path: Path) -> None:
    facts = ["Меня зовут Алексей.", "Я живу в Казани.", "Люблю котов.", "Играю на гитаре."]
    async with (
        E5Embedder(e5_config(E5_DIR)) as embedder,
        SqliteVecStore(tmp_path / "memory.sqlite", E5_DIMENSIONS) as store,
    ):
        for text, vector in zip(facts, await embedder.embed(facts, EmbedKind.PASSAGE), strict=True):
            await store.add(Fact(text, FactSource.USER, 0.8, WHEN), vector)
        timings = []
        for _ in range(20):
            started = time.perf_counter()
            (query,) = await embedder.embed(["Как меня зовут?"], EmbedKind.QUERY)
            hits = await store.search(query, limit=2)
            timings.append((time.perf_counter() - started) * 1000)

    assert hits[0].fact.text == "Меня зовут Алексей."
    assert percentile(timings, 0.95) <= SEARCH_BUDGET_MS
