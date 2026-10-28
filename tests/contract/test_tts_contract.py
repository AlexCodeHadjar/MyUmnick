"""Любой адаптер TTSPort обязан пройти эти тесты (R-57, принцип L)."""

import asyncio
import time
from contextlib import aclosing

import pytest

from tests.contract.factories import TTSCase, tts_params
from vtuber.domain import SAMPLE_WIDTH_BYTES, TTSUnavailable

# «Отмена → тишина ≤ 100 мс» (критерий Этапа 7): на синтез из этого бюджета — не больше половины.
CANCEL_LIMIT_S = 0.05
PHRASE = "Привет! Как дела?"
LONG_PHRASE = "Длинная фраза, чтобы синтез шёл заметное время и его можно было прервать. " * 3


@pytest.fixture(params=tts_params())
def case(request: pytest.FixtureRequest) -> TTSCase:
    return request.param  # type: ignore[no-any-return]  # pytest не типизирует param


async def test_returns_pcm_in_declared_format(case: TTSCase) -> None:
    async with case.available() as tts:
        chunks = [chunk async for chunk in tts.synthesize(PHRASE)]

        assert chunks
        assert all(chunk.format == tts.audio_format for chunk in chunks)
    assert all(chunk.pcm and len(chunk.pcm) % SAMPLE_WIDTH_BYTES == 0 for chunk in chunks)
    assert sum(chunk.duration_s for chunk in chunks) > 0.1


async def test_blank_phrase_gives_no_audio_and_no_error(case: TTSCase) -> None:
    async with case.available() as tts:
        assert [chunk async for chunk in tts.synthesize("  \n ")] == []


async def test_cancellation_stops_consumer_quickly_and_propagates(case: TTSCase) -> None:
    first_chunk = asyncio.Event()

    async with case.available() as tts:

        async def consume() -> None:
            async for _ in tts.synthesize(LONG_PHRASE):
                first_chunk.set()

        task = asyncio.create_task(consume())
        await asyncio.wait_for(first_chunk.wait(), timeout=10)
        started = time.perf_counter()
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task
        assert time.perf_counter() - started <= CANCEL_LIMIT_S


async def test_closing_generator_early_is_clean(case: TTSCase) -> None:
    async with case.available() as tts:
        async with aclosing(tts.synthesize(LONG_PHRASE)) as stream:
            first = await anext(stream)
        assert first.pcm
        # После закрытия движок снова готов: незакрытый синтез не мешает следующему.
        assert [chunk async for chunk in tts.synthesize(PHRASE)]


async def test_unavailable_engine_raises_tts_unavailable(case: TTSCase) -> None:
    async with case.unavailable() as tts:
        with pytest.raises(TTSUnavailable):
            async for _ in tts.synthesize(PHRASE):
                pass
