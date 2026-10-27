import asyncio
import io
from collections.abc import AsyncGenerator, Iterable, Sequence
from dataclasses import dataclass, field

from tests.fakes import FakeClock, FakeLLM
from vtuber.application.conversation import ConversationService
from vtuber.application.memory import ShortTermMemory
from vtuber.application.pipeline import ReplyPipeline
from vtuber.application.prompting import ContextBudget, ContextConfig, PromptBuilder
from vtuber.domain import Emotion, Message, Persona
from vtuber.gateway import TerminalChat, TerminalSink
from vtuber.kernel import EventBus, Telemetry
from vtuber.ports import GenerationParams, LLMPort

PERSONA = Persona(name="Мика", language="русский", description="", speech_style="", rules=())


@dataclass(slots=True)
class _Lines:
    """Строки ввода по очереди; строки после первой выдаются только после события `gate`."""

    lines: list[str]
    gate: asyncio.Event | None = None
    given: int = 0

    async def __call__(self) -> str | None:
        if self.given and self.gate is not None:
            await self.gate.wait()
        await asyncio.sleep(0)
        self.given += 1
        return self.lines.pop(0) if self.lines else None


@dataclass(slots=True)
class _SlowLLM:
    """Первый ответ: «Жила-» и навсегда ждёт (его прервут); следующие ответы — без остановки."""

    waiting: asyncio.Event = field(default_factory=asyncio.Event)
    calls: int = 0

    async def stream(
        self, messages: Sequence[Message], params: GenerationParams
    ) -> AsyncGenerator[str]:
        self.calls += 1
        yield "Жила-"
        if self.calls == 1:
            self.waiting.set()
            await asyncio.Event().wait()
        yield "была"

    async def prefill(self, messages: Sequence[Message]) -> None:
        """Не нужен."""


def _chat(llm: LLMPort, lines: Iterable[str], out: io.StringIO) -> tuple[TerminalChat, _Lines]:
    bus = EventBus()
    budget = ContextBudget(
        ContextConfig(
            max_history_tokens=1000, trim_ratio=0.5, chars_per_token=3, message_overhead_tokens=4
        )
    )
    pipeline = ReplyPipeline(
        llm, GenerationParams(max_tokens=16, temperature=0.5), Telemetry(bus, FakeClock())
    )
    service = ConversationService(pipeline, PromptBuilder(PERSONA), ShortTermMemory(budget), bus)
    reader = _Lines(list(lines))
    return TerminalChat(service, bus, reader, out), reader


async def test_reply_is_printed_with_emotion_and_ttft() -> None:
    out = io.StringIO()
    chat, _ = _chat(FakeLLM("<happy>Привет!"), ["Привет"], out)

    await chat.run()

    text = out.getvalue()
    assert "Мика: [happy] Привет!" in text
    assert "TTFT" in text


async def test_stop_command_interrupts_the_answer() -> None:
    out, llm = io.StringIO(), _SlowLLM()
    chat, reader = _chat(llm, ["Расскажи", "/stop"], out)
    reader.gate = llm.waiting

    await asyncio.wait_for(chat.run(), timeout=2)

    assert "Мика: Жила-" in out.getvalue()
    assert "прервано (user_stop)" in out.getvalue()
    assert "была" not in out.getvalue()


async def test_new_line_during_answer_interrupts_it() -> None:
    out, llm = io.StringIO(), _SlowLLM()
    chat, reader = _chat(llm, ["Расскажи", "Стоп, другое"], out)
    reader.gate = llm.waiting

    await asyncio.wait_for(chat.run(), timeout=2)

    assert "прервано (new_message)" in out.getvalue()
    assert "Жила-была" in out.getvalue()  # второй ответ дошёл целиком


async def test_exit_stops_reading_and_cancels() -> None:
    out, llm = io.StringIO(), _SlowLLM()
    chat, reader = _chat(llm, ["Расскажи", "/exit", "не дойдёт"], out)
    reader.gate = llm.waiting

    await asyncio.wait_for(chat.run(), timeout=2)

    assert "не дойдёт" not in out.getvalue()
    assert "прервано (user_stop)" in out.getvalue()


async def test_error_message_is_shown_to_user() -> None:
    out = io.StringIO()
    chat, _ = _chat(FakeLLM("Ок", fail_after=0), ["Привет"], out)

    await chat.run()

    assert "FakeLLM" in out.getvalue()


async def test_sink_remembers_first_output_time() -> None:
    clock = FakeClock()
    sink = TerminalSink(io.StringIO(), started_ns=0, clock=clock)
    clock.advance_ms(42)

    await sink.emotion(Emotion.SAD)
    clock.advance_ms(10)
    await sink.text("Жаль")

    assert sink.first_output_ns == 42_000_000


async def test_empty_lines_are_ignored_and_empty_reply_has_no_ttft() -> None:
    out = io.StringIO()
    chat, _ = _chat(FakeLLM(""), ["   ", "Привет"], out)

    await chat.run()

    assert out.getvalue().count("Мика:") == 1
    assert "TTFT" not in out.getvalue()
