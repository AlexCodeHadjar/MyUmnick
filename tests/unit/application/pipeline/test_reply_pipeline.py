import asyncio
from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass, field

import pytest

from tests.fakes import FakeClock, FakeLLM, RecordingSink
from vtuber.application.pipeline import ReplyPipeline, StreamParser
from vtuber.domain import Emotion, GenerationFailed, Message, MetricRecorded, Role
from vtuber.kernel import EventBus, Telemetry
from vtuber.ports import GenerationParams

MESSAGES = (Message(Role.USER, "Привет"),)
PARAMS = GenerationParams(max_tokens=32, temperature=0.5)


@dataclass(slots=True)
class _GatedLLM:
    """Отдаёт первую порцию и ждёт `release`; помнит, закрыли ли поток.

    `waiting` взводится, когда конвейер уже доставил первую порцию и запросил следующую.
    """

    first: str
    rest: str
    release: asyncio.Event = field(default_factory=asyncio.Event)
    waiting: asyncio.Event = field(default_factory=asyncio.Event)
    closed: bool = False

    async def stream(
        self, messages: Sequence[Message], params: GenerationParams
    ) -> AsyncGenerator[str]:
        try:
            yield self.first
            self.waiting.set()
            await self.release.wait()
            yield self.rest
        finally:
            self.closed = True

    async def prefill(self, messages: Sequence[Message]) -> None:
        """Не нужен в этих тестах."""


def _pipeline(llm: FakeLLM | _GatedLLM, telemetry: Telemetry | None = None) -> ReplyPipeline:
    return ReplyPipeline(llm, PARAMS, telemetry or Telemetry(EventBus(), FakeClock()))


async def test_text_and_emotions_reach_sink_in_order_then_done() -> None:
    sink, parser = RecordingSink(), StreamParser()

    await _pipeline(FakeLLM("<happy>Привет! <sad>Пока.", chunk_size=3)).run(MESSAGES, sink, parser)

    assert sink.kinds()[0] == "emotion"
    assert sink.kinds()[-1] == "done"
    assert sink.emotions() == [Emotion.HAPPY, Emotion.SAD]
    assert sink.shown_text() == "Привет! Пока."
    assert parser.full_text == "<happy>Привет! <sad>Пока."


async def test_text_reaches_sink_before_generation_ends() -> None:
    llm, sink = _GatedLLM(first="Привет", rest=", друг!"), RecordingSink()
    run = asyncio.create_task(_pipeline(llm).run(MESSAGES, sink, StreamParser()))

    await llm.waiting.wait()
    assert sink.shown_text() == "Привет"
    assert "done" not in sink.kinds()

    llm.release.set()
    await run
    assert sink.shown_text() == "Привет, друг!"


async def test_cancellation_closes_llm_stream_and_keeps_shown_part() -> None:
    llm, sink, parser = (
        _GatedLLM(first="<happy>Жила-", rest="была"),
        RecordingSink(),
        StreamParser(),
    )
    run = asyncio.create_task(_pipeline(llm).run(MESSAGES, sink, parser))
    await llm.waiting.wait()

    run.cancel()
    with pytest.raises(asyncio.CancelledError):
        await run

    assert llm.closed
    assert "done" not in sink.kinds()
    assert parser.full_text == "<happy>Жила-"


async def test_generation_error_propagates_without_done() -> None:
    llm = FakeLLM("Привет, как дела?", chunk_size=4, fail_after=2, error_type=GenerationFailed)
    sink = RecordingSink()

    with pytest.raises(GenerationFailed):
        await _pipeline(llm).run(MESSAGES, sink, StreamParser())

    assert sink.shown_text() == "Привет, "
    assert "done" not in sink.kinds()


async def test_empty_reply_still_ends_with_done() -> None:
    sink = RecordingSink()

    await _pipeline(FakeLLM("")).run(MESSAGES, sink, StreamParser())

    assert sink.kinds() == ["done"]


async def test_unfinished_tag_at_end_is_flushed_away() -> None:
    sink = RecordingSink()

    await _pipeline(FakeLLM("Пока <hap")).run(MESSAGES, sink, StreamParser())

    assert sink.shown_text() == "Пока "


async def test_time_to_first_token_and_stream_are_measured() -> None:
    bus, clock = EventBus(), FakeClock()
    names: list[str] = []
    both_published = asyncio.Event()

    async def collect(event: MetricRecorded) -> None:
        names.append(event.name)
        if len(names) == 2:
            both_published.set()

    bus.subscribe(MetricRecorded, collect)
    telemetry = Telemetry(bus, clock)

    await _pipeline(FakeLLM("Привет"), telemetry).run(MESSAGES, RecordingSink(), StreamParser())
    runner = asyncio.create_task(telemetry.run())
    await asyncio.wait_for(both_published.wait(), timeout=1)
    runner.cancel()

    assert names == ["llm.first_token", "llm.stream"]
