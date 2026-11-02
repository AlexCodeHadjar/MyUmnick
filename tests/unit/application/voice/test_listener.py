"""Голосовой ввод целиком на фейках (S-11.3): фраза, гипотезы, перебивание, сбои."""

import array
import asyncio
from dataclasses import dataclass, field

from tests.fakes import FakeSTT, FakeVad
from vtuber.application.voice import SegmenterConfig, VoiceConfig, VoiceListener
from vtuber.domain import AudioChunk, AudioFormat

RATE = AudioFormat(16_000)
SEGMENTS = SegmenterConfig(
    threshold=0.5,
    start_ms=96,
    end_silence_ms=320,
    barge_in_ms=300,
    pre_roll_ms=64,
    max_phrase_s=20.0,
)
CFG = VoiceConfig(interim_ms=320, min_phrase_ms=200, segmenter=SEGMENTS)


def _audio(seconds: float, *, loud: bool) -> AudioChunk:
    count = round(seconds * RATE.sample_rate)
    value = 8000 if loud else 0
    return AudioChunk(RATE, array.array("h", [value] * count).tobytes())


@dataclass(slots=True)
class _Events:
    barge_ins: int = 0
    hypotheses: list[str] = field(default_factory=list)
    finals: list[str] = field(default_factory=list)

    async def barge_in(self) -> None:
        self.barge_ins += 1

    async def hypothesis(self, text: str) -> None:
        self.hypotheses.append(text)

    async def final(self, text: str, ended_ns: int) -> None:
        self.finals.append(text)


async def _settle(rounds: int = 2000) -> None:
    for _ in range(rounds):
        await asyncio.sleep(0)


async def _listen(stt: FakeSTT, *chunks: AudioChunk) -> _Events:
    events = _Events()
    listener = VoiceListener(FakeVad(), stt, events, CFG)
    loop = asyncio.create_task(listener.run())
    for chunk in chunks:
        listener.feed(chunk)
    await _settle()
    loop.cancel()
    await asyncio.wait([loop])
    return events


async def test_phrase_becomes_final_text_with_barge_in_and_interim() -> None:
    stt = FakeSTT("как дела")

    events = await _listen(stt, _audio(1.0, loud=True), _audio(0.5, loud=False))

    assert events.finals == ["как дела"]
    assert events.barge_ins == 1
    assert events.hypotheses
    assert stt.calls[-1][1] is True
    assert {final for _, final in stt.calls[:-1]} == {False}


async def test_silence_gives_nothing() -> None:
    stt = FakeSTT()

    events = await _listen(stt, _audio(2.0, loud=False))

    assert events.finals == []
    assert stt.calls == []


async def test_too_short_phrase_is_not_transcribed() -> None:
    cfg = VoiceConfig(interim_ms=10_000, min_phrase_ms=5000, segmenter=SEGMENTS)
    stt, events = FakeSTT(), _Events()
    listener = VoiceListener(FakeVad(), stt, events, cfg)
    loop = asyncio.create_task(listener.run())
    listener.feed(_audio(0.5, loud=True))
    listener.feed(_audio(0.5, loud=False))
    await _settle()
    loop.cancel()

    assert events.finals == []
    assert stt.calls == []


async def test_empty_transcript_is_not_a_reply() -> None:
    events = await _listen(FakeSTT(""), _audio(1.0, loud=True), _audio(0.5, loud=False))

    assert events.finals == []


async def test_stt_failure_keeps_listening() -> None:
    events = await _listen(
        FakeSTT(available=False), _audio(1.0, loud=True), _audio(0.5, loud=False)
    )

    assert events.finals == []


async def test_frames_of_any_size_are_cut_into_detector_windows() -> None:
    events = _Events()
    listener = VoiceListener(FakeVad(), FakeSTT("ок"), events, CFG)
    loop = asyncio.create_task(listener.run())
    speech = _audio(1.0, loud=True).pcm
    for start in range(0, len(speech), 640):
        listener.feed(AudioChunk(RATE, speech[start : start + 640]))
    listener.feed(_audio(0.5, loud=False))
    await _settle()
    loop.cancel()

    assert events.finals == ["ок"]


async def test_wrong_sample_rate_is_dropped() -> None:
    events = await _listen(FakeSTT("ок"), AudioChunk(AudioFormat(48_000), bytes(9600)))

    assert events.finals == []
