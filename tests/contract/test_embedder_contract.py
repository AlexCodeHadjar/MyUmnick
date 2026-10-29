"""Любой адаптер EmbedderPort обязан пройти эти тесты (R-57, принцип L)."""

import math

import pytest

from tests.contract.memory_factories import EmbedderCase, embedder_params
from vtuber.domain import EmbedKind, MemoryUnavailable, Vector

FACT = "Меня зовут Алексей, я живу в Казани."
QUERY_CLOSE = "Как зовут пользователя?"
UNRELATED = "Сегодня на ужин будет пицца с грибами."


@pytest.fixture(params=embedder_params())
def case(request: pytest.FixtureRequest) -> EmbedderCase:
    return request.param  # type: ignore[no-any-return]  # pytest не типизирует param


def _dot(a: Vector, b: Vector) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


async def test_one_unit_vector_per_text_in_order(case: EmbedderCase) -> None:
    async with case.available() as embedder:
        texts = [FACT, UNRELATED, ""]
        vectors = await embedder.embed(texts, EmbedKind.PASSAGE)

        assert len(vectors) == len(texts)
        assert all(len(vector) == embedder.dimensions for vector in vectors)
    assert all(math.isclose(math.sqrt(_dot(v, v)), 1.0, abs_tol=1e-3) for v in vectors)


async def test_empty_batch_is_empty_result(case: EmbedderCase) -> None:
    async with case.available() as embedder:
        assert await embedder.embed([], EmbedKind.QUERY) == []


async def test_same_text_same_vector_in_any_batch(case: EmbedderCase) -> None:
    async with case.available() as embedder:
        (alone,) = await embedder.embed([FACT], EmbedKind.PASSAGE)
        _, in_batch = await embedder.embed([UNRELATED, FACT], EmbedKind.PASSAGE)

    assert _dot(alone, in_batch) == pytest.approx(1.0, abs=1e-4)


async def test_related_query_is_closer_than_unrelated_text(case: EmbedderCase) -> None:
    async with case.available() as embedder:
        fact, unrelated = await embedder.embed([FACT, UNRELATED], EmbedKind.PASSAGE)
        (query,) = await embedder.embed([QUERY_CLOSE], EmbedKind.QUERY)

    assert _dot(query, fact) > _dot(query, unrelated)


async def test_unavailable_model_raises_memory_unavailable(case: EmbedderCase) -> None:
    async with case.unavailable() as embedder:
        with pytest.raises(MemoryUnavailable):
            await embedder.embed([FACT], EmbedKind.QUERY)
