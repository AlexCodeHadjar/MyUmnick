"""Сообщение об озвученной фразе (субтитры): когда зазвучит и сколько продлится."""

import asyncio
from collections.abc import AsyncGenerator

import pytest

from tests.fakes import FakeClock, RecordingSink
from vtuber.application.pipeline import PhraseQueue, Speaker
from vtuber.domain import AudioChunk, AudioFormat, PhraseVoiced, TTSUnavailable
from vtuber.kernel import EventBus, Telemetry

FMT = AudioFormat(sample_rate=1000)
PHRASE_S = 5.0


class _TTS:
    """Мгновенный синтез: `PHRASE_S` секунд звука двумя кадрами на любую фразу."""

    @property
    def audio_format(self) -> AudioFormat:
        return FMT

    async def synthesize(self, text: str) -> AsyncGenerator[AudioChunk]:
        half = b"\x00" * int(PHRASE_S / 2 * FMT.bytes_per_second)
        yield AudioChunk(FMT, half)
        yield AudioChunk(FMT, half)


class _BrokenTTS(_TTS):
    async def synthesize(self, text: str) -> AsyncGenerator[AudioChunk]:
        chunks: tuple[AudioChunk, ...] = ()
        for chunk in chunks:  # генератор, как у настоящего движка: сбой — при первом чтении
            yield chunk
        raise TTSUnavailable("нет модели")


async def _voiced(tts: _TTS, *phrases: str) -> list[PhraseVoiced]:
    heard: list[PhraseVoiced] = []

    async def on_phrase(event: PhraseVoiced) -> None:
        heard.append(event)

    queue: PhraseQueue = asyncio.Queue()
    for phrase in (*phrases, None):
        queue.put_nowait(phrase)
    speaker = Speaker(tts, Telemetry(EventBus(), FakeClock()), None, on_phrase)
    await speaker.run(queue, RecordingSink())
    return heard


async def test_second_phrase_starts_after_sound_of_first() -> None:
    first, second = await _voiced(_TTS(), "Первая.", "Вторая.")

    assert (first.text, second.text) == ("Первая.", "Вторая.")
    assert first.starts_in_s == pytest.approx(0, abs=0.5)
    assert first.duration_s == pytest.approx(PHRASE_S)
    assert second.starts_in_s == pytest.approx(PHRASE_S, abs=0.5)
    assert second.duration_s == pytest.approx(PHRASE_S)


async def test_subtitle_keeps_original_text_not_normalized() -> None:
    (event,) = await _voiced(_TTS(), "В 2024 году.")

    assert event.text == "В 2024 году."


async def test_no_event_when_voice_is_unavailable() -> None:
    assert await _voiced(_BrokenTTS(), "Первая.") == []
