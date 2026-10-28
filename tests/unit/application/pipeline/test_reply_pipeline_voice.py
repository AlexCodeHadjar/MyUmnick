"""TTS-ветка ReplyPipeline (S-7.5): фразы озвучиваются, пока LLM ещё пишет (T-02)."""

import asyncio
from collections.abc import AsyncGenerator, Callable, Sequence
from dataclasses import dataclass, field

import pytest

from tests.fakes import FakeClock, FakeLLM, FakeTTS, RecordingSink
from vtuber.application.pipeline import ChunkerConfig, ReplyPipeline, StreamParser, Voice
from vtuber.domain import (
    GenerationFailed,
    LLMUnavailable,
    Message,
    MetricRecorded,
    Role,
    TTSUnavailable,
)
from vtuber.kernel import EventBus, Telemetry
from vtuber.ports import GenerationParams

MESSAGES = (Message(Role.USER, "Привет"),)
PARAMS = GenerationParams(max_tokens=32, temperature=0.5)
CHUNKER = ChunkerConfig(first_min_words=4, next_min_words=10, max_words=25)


@dataclass(slots=True)
class _GatedLLM:
    """Отдаёт первую порцию и ждёт `release`, пока тест смотрит, что уже успело случиться."""

    first: str
    rest: str
    release: asyncio.Event = field(default_factory=asyncio.Event)
    closed: bool = False

    async def stream(
        self, messages: Sequence[Message], params: GenerationParams
    ) -> AsyncGenerator[str]:
        try:
            yield self.first
            await self.release.wait()
            yield self.rest
        finally:
            self.closed = True

    async def prefill(self, messages: Sequence[Message]) -> None:
        """Не нужен в этих тестах."""


def _pipeline(
    llm: FakeLLM | _GatedLLM, tts: FakeTTS, telemetry: Telemetry | None = None
) -> ReplyPipeline:
    return ReplyPipeline(
        llm, PARAMS, telemetry or Telemetry(EventBus(), FakeClock()), Voice(tts, CHUNKER)
    )


async def _until(check: Callable[[], bool]) -> None:
    for _ in range(200):
        if check():
            return
        await asyncio.sleep(0.005)
    msg = "условие не наступило за секунду"
    raise AssertionError(msg)


async def test_first_phrase_goes_to_tts_before_llm_finishes() -> None:
    llm = _GatedLLM(first="Ну что ж, раз уж ты спрашиваешь, расскажу", rest=" тебе сказку.")
    tts, sink = FakeTTS(), RecordingSink()
    run = asyncio.create_task(_pipeline(llm, tts).run(MESSAGES, sink, StreamParser()))

    await _until(lambda: bool(sink.audio_chunks()))
    assert tts.phrases == ["Ну что ж, раз уж ты спрашиваешь,"]
    assert "done" not in sink.kinds()

    llm.release.set()
    await run
    assert tts.phrases == ["Ну что ж, раз уж ты спрашиваешь,", "расскажу тебе сказку."]
    assert sink.kinds()[-1] == "done"


async def test_phrases_are_normalized_and_tags_are_not_spoken() -> None:
    tts, sink = FakeTTS(), RecordingSink()

    await _pipeline(FakeLLM("<happy>У меня 2 кота и 50% счастья!", chunk_size=4), tts).run(
        MESSAGES, sink, StreamParser()
    )

    assert tts.phrases == ["У меня два кота и пятьдесят процентов счастья!"]
    assert sink.shown_text() == "У меня 2 кота и 50% счастья!"
    assert sink.audio_chunks()
    assert sink.kinds()[-1] == "done"


async def test_turn_ends_only_after_last_audio() -> None:
    tts, sink = FakeTTS(rtf=0.2, chunk_ms=50), RecordingSink()

    await _pipeline(FakeLLM("Привет! Как дела?", chunk_size=20), tts).run(
        MESSAGES, sink, StreamParser()
    )

    kinds = sink.kinds()
    assert kinds.index("done") > max(i for i, kind in enumerate(kinds) if kind == "audio")


async def test_unavailable_tts_keeps_text_and_finishes_turn() -> None:
    sink = RecordingSink()

    await _pipeline(FakeLLM("Привет! Как дела?"), FakeTTS(fail_after=0)).run(
        MESSAGES, sink, StreamParser()
    )

    assert sink.shown_text() == "Привет! Как дела?"
    assert sink.audio_chunks() == []
    assert sink.kinds()[-1] == "done"


async def test_failed_phrase_is_skipped_and_next_ones_are_spoken() -> None:
    tts = FakeTTS(fail_after=1, error_type=GenerationFailed, chunk_ms=20)
    sink = RecordingSink()

    await _pipeline(FakeLLM("Первая фраза здесь. Вторая фраза тут."), tts).run(
        MESSAGES, sink, StreamParser()
    )

    assert tts.phrases == ["Первая фраза здесь.", "Вторая фраза тут."]
    assert len(sink.audio_chunks()) == 2  # от каждой фразы — первый фрагмент до сбоя
    assert sink.kinds()[-1] == "done"


async def test_cancellation_stops_llm_and_speech_without_done() -> None:
    llm = _GatedLLM(first="Раз два три четыре, пять", rest=" шесть.")
    tts, sink = FakeTTS(rtf=1.0, chunk_ms=50, ms_per_char=200), RecordingSink()
    run = asyncio.create_task(_pipeline(llm, tts).run(MESSAGES, sink, StreamParser()))
    await _until(lambda: bool(sink.audio_chunks()))

    run.cancel()
    with pytest.raises(asyncio.CancelledError):
        await run

    spoken = len(sink.audio_chunks())
    await asyncio.sleep(0.1)
    assert llm.closed
    assert len(sink.audio_chunks()) == spoken
    assert "done" not in sink.kinds()


async def test_llm_error_stops_speech_and_propagates() -> None:
    sink = RecordingSink()

    with pytest.raises(LLMUnavailable):
        await _pipeline(FakeLLM("Привет", fail_after=0), FakeTTS()).run(
            MESSAGES, sink, StreamParser()
        )
    assert "done" not in sink.kinds()


async def test_first_audio_metric_is_recorded_once_and_only_with_sound() -> None:
    async def metrics_of(tts: FakeTTS) -> list[str]:
        bus = EventBus()
        names: list[str] = []

        async def collect(event: MetricRecorded) -> None:
            names.append(event.name)

        bus.subscribe(MetricRecorded, collect)
        telemetry = Telemetry(bus, FakeClock())
        await _pipeline(FakeLLM("Раз. Два. Три."), tts, telemetry).run(
            MESSAGES, RecordingSink(), StreamParser()
        )
        runner = asyncio.create_task(telemetry.run())
        await _until(lambda: telemetry.pending == 0)
        await asyncio.sleep(0)
        runner.cancel()
        return names

    with_sound = await metrics_of(FakeTTS())
    silent = await metrics_of(FakeTTS(fail_after=0, error_type=TTSUnavailable))

    assert with_sound.count("tts.first_audio") == 1
    assert with_sound.count("tts.phrase") == 3
    assert "tts.first_audio" not in silent
