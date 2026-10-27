import asyncio
import time

import pytest

from tests.fakes import FakeTTS
from tests.fakes.fake_tts import tone_pcm
from vtuber.domain import AudioChunk, GenerationFailed, TTSUnavailable


async def _collect(tts: FakeTTS, phrase: str) -> list[AudioChunk]:
    return [chunk async for chunk in tts.synthesize(phrase)]


async def test_duration_follows_phrase_length_split_into_chunks() -> None:
    tts = FakeTTS(sample_rate=16_000, ms_per_char=50, chunk_ms=100)

    chunks = await _collect(tts, "  Привет!  ")

    # 7 символов × 50 мс = 350 мс → три фрагмента по 100 мс и хвост 50 мс.
    assert [round(chunk.duration_s, 3) for chunk in chunks] == [0.1, 0.1, 0.1, 0.05]
    assert all(chunk.format == tts.audio_format for chunk in chunks)
    assert tts.phrases == ["  Привет!  "]


async def test_blank_phrase_gives_no_audio() -> None:
    assert await _collect(FakeTTS(), "   ") == []


async def test_chunks_join_into_one_continuous_tone() -> None:
    chunks = await _collect(FakeTTS(sample_rate=8000, ms_per_char=100, chunk_ms=30), "абв")

    assert b"".join(chunk.pcm for chunk in chunks) == tone_pcm(0, 2400, 8000)
    assert any(chunk.pcm.strip(b"\x00") for chunk in chunks)


async def test_rtf_paces_synthesis() -> None:
    # 10 символов × 60 мс = 0.6 с звука; RTF 0.5 → около 0.3 с синтеза.
    tts = FakeTTS(rtf=0.5, chunk_ms=200)

    started = time.perf_counter()
    await _collect(tts, "0123456789")

    assert 0.25 <= time.perf_counter() - started <= 0.6


async def test_fails_after_given_number_of_chunks() -> None:
    stream = FakeTTS(fail_after=1, error_type=GenerationFailed).synthesize("Длинная фраза")

    await anext(stream)
    with pytest.raises(GenerationFailed):
        await anext(stream)


async def test_fail_after_zero_means_engine_is_unavailable_even_for_blank_phrase() -> None:
    with pytest.raises(TTSUnavailable):
        await _collect(FakeTTS(fail_after=0), " ")


async def test_yields_to_event_loop_between_chunks() -> None:
    ticks = 0

    async def ticker() -> None:
        nonlocal ticks
        while True:
            ticks += 1
            await asyncio.sleep(0)

    task = asyncio.create_task(ticker())
    await _collect(FakeTTS(chunk_ms=10), "фраза из нескольких фрагментов")
    task.cancel()

    assert ticks > 1
