"""Любой адаптер MemoryStorePort обязан пройти эти тесты (R-57, принцип L)."""

import math
from datetime import UTC, datetime

import pytest

from tests.contract.memory_factories import StoreCase, store_params
from vtuber.domain import Fact, FactSource, MemoryUnavailable, Vector

DIMS = 8
WHEN = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)


@pytest.fixture(params=store_params())
def case(request: pytest.FixtureRequest) -> StoreCase:
    return request.param  # type: ignore[no-any-return]  # pytest не типизирует param


def _unit(*values: float) -> Vector:
    padded = [*values, *([0.0] * (DIMS - len(values)))]
    norm = math.sqrt(sum(v * v for v in padded))
    return tuple(v / norm for v in padded)


def _fact(text: str) -> Fact:
    return Fact(text, FactSource.USER, importance=0.5, created_at=WHEN)


async def test_empty_store_finds_nothing(case: StoreCase) -> None:
    async with case.available(DIMS) as store:
        assert await store.search(_unit(1), limit=3) == []


async def test_fact_is_found_by_its_own_vector_first(case: StoreCase) -> None:
    async with case.available(DIMS) as store:
        cats = await store.add(_fact("Любит котов"), _unit(1, 0.1))
        await store.add(_fact("Живёт в Казани"), _unit(0, 1))

        (best, *_) = await store.search(_unit(1, 0.1), limit=2)

    assert best.id == cats
    assert best.fact == _fact("Любит котов")
    assert best.score == pytest.approx(1.0, abs=1e-4)


async def test_hits_sorted_by_score_and_limited(case: StoreCase) -> None:
    async with case.available(DIMS) as store:
        for i in range(5):
            await store.add(_fact(f"факт {i}"), _unit(1, i))

        hits = await store.search(_unit(1, 0), limit=3)

    assert len(hits) == 3
    scores = [hit.score for hit in hits]
    assert scores == sorted(scores, reverse=True)
    assert len({hit.id for hit in hits}) == 3


async def test_fact_fields_survive_round_trip(case: StoreCase) -> None:
    fact = Fact("Собирается в отпуск в мае", FactSource.EXTRACTED, 0.8, WHEN)
    async with case.available(DIMS) as store:
        await store.add(fact, _unit(0, 0, 1))
        (hit,) = await store.search(_unit(0, 0, 1), limit=1)

    assert hit.fact == fact


@pytest.mark.parametrize("bad", [(1.0,), (*_unit(1), 0.0)])
async def test_wrong_dimension_is_value_error(case: StoreCase, bad: Vector) -> None:
    async with case.available(DIMS) as store:
        with pytest.raises(ValueError, match="размерност"):
            await store.add(_fact("x"), bad)
        with pytest.raises(ValueError, match="размерност"):
            await store.search(bad, limit=1)


async def test_limit_below_one_is_value_error(case: StoreCase) -> None:
    async with case.available(DIMS) as store:
        with pytest.raises(ValueError, match="limit"):
            await store.search(_unit(1), limit=0)


async def test_unavailable_store_raises_memory_unavailable(case: StoreCase) -> None:
    async with case.unavailable(DIMS) as store:
        with pytest.raises(MemoryUnavailable):
            await store.add(_fact("x"), _unit(1))
        with pytest.raises(MemoryUnavailable):
            await store.search(_unit(1), limit=1)


async def test_all_facts_and_remove_note(case: StoreCase) -> None:
    async with case.available(8) as store:
        kept = Fact("Любит котов", FactSource.USER, 0.5, WHEN, note="оставить")
        gone = Fact("Живёт в Казани", FactSource.USER, 0.5, WHEN, note="удалить")
        await store.add(kept, _unit(0.0, 1.0))
        await store.add(gone, _unit(1.0, 0.0))
        assert await store.all_facts() == [kept, gone]
        await store.remove_note("удалить")
        assert await store.all_facts() == [kept]
        assert [hit.fact for hit in await store.search(_unit(1.0, 0.0), 5)] == [kept]
