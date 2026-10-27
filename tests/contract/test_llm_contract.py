"""Любой адаптер LLMPort обязан пройти эти тесты (R-57)."""

import asyncio
import time

import pytest

from tests.contract.factories import LLMCase, llm_cases
from vtuber.domain import LLMUnavailable, Message, Role
from vtuber.ports import GenerationParams

CANCEL_LIMIT_S = 0.05
MESSAGES = (Message(Role.USER, "Привет! Расскажи что-нибудь."),)
PARAMS = GenerationParams(max_tokens=64, temperature=0.7)


@pytest.fixture(params=llm_cases(), ids=lambda case: case.name)
def case(request: pytest.FixtureRequest) -> LLMCase:
    return request.param  # type: ignore[no-any-return]  # pytest не типизирует param


async def test_stream_yields_non_empty_text_deltas(case: LLMCase) -> None:
    async with case.available() as llm:
        deltas = [delta async for delta in llm.stream(MESSAGES, PARAMS)]

    assert deltas
    assert all(isinstance(delta, str) for delta in deltas)
    assert "".join(deltas).strip()


async def test_cancellation_stops_consumer_quickly_and_propagates(case: LLMCase) -> None:
    first_delta = asyncio.Event()

    async with case.available() as llm:

        async def consume() -> None:
            async for _ in llm.stream(MESSAGES, PARAMS):
                first_delta.set()

        task = asyncio.create_task(consume())
        await asyncio.wait_for(first_delta.wait(), timeout=5)
        started = time.perf_counter()
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task
        assert time.perf_counter() - started <= CANCEL_LIMIT_S


async def test_unavailable_backend_raises_llm_unavailable_on_stream(case: LLMCase) -> None:
    async with case.unavailable() as llm:
        with pytest.raises(LLMUnavailable):
            async for _ in llm.stream(MESSAGES, PARAMS):
                pass


async def test_prefill_completes_on_available_backend(case: LLMCase) -> None:
    async with case.available() as llm:
        await llm.prefill(MESSAGES)


async def test_unavailable_backend_raises_llm_unavailable_on_prefill(case: LLMCase) -> None:
    async with case.unavailable() as llm:
        with pytest.raises(LLMUnavailable):
            await llm.prefill(MESSAGES)
