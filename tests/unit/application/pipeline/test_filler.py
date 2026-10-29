"""Междометия-заглушки (S-8.3, T-17): звучат, только если ответ опаздывает, и не накладываются."""

import asyncio
from collections.abc import AsyncGenerator, Callable, Sequence
from dataclasses import dataclass, field

from tests.fakes import FakeClock, FakeLLM, FakeTTS, RecordingSink
from vtuber.application.pipeline import (
    AudioOut,
    ChunkerConfig,
    FillerBank,
    FillerConfig,
    ReplyPipeline,
    StreamParser,
    Voice,
)
from vtuber.domain import AudioChunk, AudioFormat, Message, Role
from vtuber.kernel import EventBus, Telemetry
from vtuber.ports import GenerationParams

MESSAGES = (Message(Role.USER, "Привет"),)
PARAMS = GenerationParams(max_tokens=32, temperature=0.5)
CHUNKER = ChunkerConfig(first_min_words=4, next_min_words=10, max_words=25)
PHRASES = ("Хм…", "Так…")


def _config(*, enabled: bool = True, after_ms: int = 10) -> FillerConfig:
    return FillerConfig(enabled=enabled, after_ms=after_ms, phrases=PHRASES)


async def _bank(after_ms: int = 10) -> FillerBank:
    bank = FillerBank(_config(after_ms=after_ms))
    await bank.prepare(FakeTTS(ms_per_char=100))
    return bank


@dataclass(slots=True)
class _GatedLLM:
    """Ответ задерживается до `release`: тест решает, когда звук ответа «готов»."""

    text: str
    release: asyncio.Event = field(default_factory=asyncio.Event)

    async def stream(
        self, messages: Sequence[Message], params: GenerationParams
    ) -> AsyncGenerator[str]:
        await self.release.wait()
        yield self.text

    async def prefill(self, messages: Sequence[Message]) -> None:
        """Не нужен в этих тестах."""


@dataclass(slots=True)
class _SlowSink(RecordingSink):
    """Отдача фрагмента занимает время — как отправка по сокету."""

    delay_s: float = 0.002

    async def audio(self, chunk: AudioChunk) -> None:
        await asyncio.sleep(self.delay_s)
        await RecordingSink.audio(self, chunk)


def _pipeline(llm: FakeLLM | _GatedLLM, bank: FillerBank) -> ReplyPipeline:
    voice = Voice(FakeTTS(), CHUNKER, bank)
    return ReplyPipeline(llm, PARAMS, Telemetry(EventBus(), FakeClock()), voice)


async def _until(check: Callable[[], bool]) -> None:
    for _ in range(500):
        if check():
            return
        await asyncio.sleep(0.002)
    raise AssertionError("условие не наступило")


async def test_bank_synthesizes_phrases_once_and_rotates() -> None:
    tts = FakeTTS()
    bank = FillerBank(_config())

    await bank.prepare(tts)

    assert bank.ready
    assert tts.phrases == list(PHRASES)
    first, second, third = bank.next_clip(), bank.next_clip(), bank.next_clip()
    assert first is not second
    assert third is first


async def test_disabled_bank_stays_silent() -> None:
    tts = FakeTTS()
    bank = FillerBank(_config(enabled=False))

    await bank.prepare(tts)

    assert not bank.ready
    assert tts.phrases == []


async def test_late_answer_gets_filler_first_then_answer_whole() -> None:
    bank = await _bank()
    clips = [bank.next_clip(), bank.next_clip()]
    llm = _GatedLLM("Привет! Рада тебя слышать, как дела?")
    sink = RecordingSink()
    turn = asyncio.create_task(_pipeline(llm, bank).run(MESSAGES, sink, StreamParser()))

    await _until(lambda: len(sink.audio_chunks()) >= len(clips[0]))
    llm.release.set()
    await turn

    # FakeTTS даёт одинаковый тон для любой фразы — фрагменты различаются по объекту.
    chunks = sink.audio_chunks()
    clip = clips[0]
    assert all(got is want for got, want in zip(chunks, clip, strict=False))
    assert not any(chunk is filler for chunk in chunks[len(clip) :] for filler in clip)
    assert len(chunks) > len(clip)
    assert sink.kinds()[-1] == "done"


async def test_fast_answer_has_no_filler() -> None:
    bank = await _bank(after_ms=5000)
    fillers = [chunk for clip in (bank.next_clip(), bank.next_clip()) for chunk in clip]
    sink = RecordingSink()

    await _pipeline(FakeLLM("Привет! Рада тебя слышать."), bank).run(MESSAGES, sink, StreamParser())

    assert sink.audio_chunks()
    assert not any(chunk is filler for chunk in sink.audio_chunks() for filler in fillers)


async def test_answer_during_filler_waits_and_does_not_interleave() -> None:
    fmt = AudioFormat(24_000)
    clip = tuple(AudioChunk(fmt, bytes([i]) * 2) for i in range(5))
    answer = AudioChunk(fmt, b"\xff\xff")
    sink = _SlowSink()
    out = AudioOut(sink)

    filler = asyncio.create_task(out.filler(clip))
    await _until(lambda: len(sink.audio_chunks()) >= 1)
    await out.answer(answer)

    assert await filler
    assert sink.audio_chunks() == [*clip, answer]


async def test_filler_after_answer_started_is_skipped() -> None:
    fmt = AudioFormat(24_000)
    sink = RecordingSink()
    out = AudioOut(sink)

    await out.answer(AudioChunk(fmt, b"\x01\x00"))

    assert not await out.filler((AudioChunk(fmt, b"\x02\x00"),))
    assert len(sink.audio_chunks()) == 1


async def test_turn_ending_before_deadline_cancels_filler() -> None:
    bank = await _bank(after_ms=50)
    sink = RecordingSink()

    # Ответ без слов — звука нет, ход кончается раньше срока междометия.
    await _pipeline(FakeLLM("<happy>"), bank).run(MESSAGES, sink, StreamParser())
    await asyncio.sleep(0.1)

    assert sink.audio_chunks() == []
