"""Speculative prefill (T-05, S-9.2): черновик реплики прогревает кэш LLM между ходами."""

import asyncio
from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass, field

from tests.fakes import FakeClock, FakeLLM, RecordingSink
from vtuber.application.conversation import ConversationService
from vtuber.application.memory import ShortTermMemory
from vtuber.application.pipeline import ReplyPipeline
from vtuber.application.prompting import ContextBudget, ContextConfig, PromptBuilder
from vtuber.domain import GenerationFailed, Message, Persona, Role
from vtuber.kernel import EventBus, Telemetry
from vtuber.ports import GenerationParams, LLMPort

PERSONA = Persona(name="Мика", language="русский", description="", speech_style="", rules=())
BUDGET = ContextBudget(
    ContextConfig(
        max_history_tokens=10_000, trim_ratio=0.5, chars_per_token=3, message_overhead_tokens=4
    )
)


@dataclass(slots=True)
class _SlowPrefillLLM:
    """Прогрев висит до `release`; отменённые прогревы считаются."""

    prefills: list[Sequence[Message]] = field(default_factory=list)
    cancelled: int = 0
    release: asyncio.Event = field(default_factory=asyncio.Event)
    fail: bool = False

    async def stream(
        self, messages: Sequence[Message], params: GenerationParams
    ) -> AsyncGenerator[str]:
        yield "Ок."

    async def prefill(self, messages: Sequence[Message]) -> None:
        self.prefills.append(messages)
        if self.fail:
            msg = "сервер ответил 500"
            raise GenerationFailed(msg)
        try:
            await self.release.wait()
        except asyncio.CancelledError:
            self.cancelled += 1
            raise


@dataclass(slots=True)
class _GatedStreamLLM:
    """Ответ висит до `gate`: ход идёт, пока тест не отпустит."""

    prefills: list[Sequence[Message]] = field(default_factory=list)
    gate: asyncio.Event = field(default_factory=asyncio.Event)

    async def stream(
        self, messages: Sequence[Message], params: GenerationParams
    ) -> AsyncGenerator[str]:
        await self.gate.wait()
        yield "Ок."

    async def prefill(self, messages: Sequence[Message]) -> None:
        self.prefills.append(messages)


def _service(llm: LLMPort) -> tuple[ConversationService, ShortTermMemory]:
    bus = EventBus()
    memory = ShortTermMemory(BUDGET)
    pipeline = ReplyPipeline(
        llm, GenerationParams(max_tokens=32, temperature=0.5), Telemetry(bus, FakeClock())
    )
    return ConversationService(pipeline, PromptBuilder(PERSONA), memory, bus), memory


async def _settle() -> None:
    for _ in range(5):
        await asyncio.sleep(0)


async def test_draft_prefills_full_prompt_ending_with_draft() -> None:
    llm = FakeLLM("Ок.")
    service, _ = _service(llm)
    await service.handle("Привет", RecordingSink())
    await service.wait_idle()

    service.typing("  Как дела  ")
    await _settle()

    (messages,) = llm.prefills
    assert messages[0].role is Role.SYSTEM
    assert messages[-1] == Message(Role.USER, "Как дела")
    # История прошлого хода — в промпте прогрева, как будет и в настоящем запросе.
    assert Message(Role.USER, "Привет") in messages


async def test_empty_or_repeated_draft_is_not_prefilled_again() -> None:
    llm = FakeLLM("Ок.")
    service, _ = _service(llm)

    for draft in ("", "   ", "Привет", "Привет", " Привет "):
        service.typing(draft)
        await _settle()

    assert len(llm.prefills) == 1


async def test_new_draft_cancels_stale_prefill() -> None:
    llm = _SlowPrefillLLM()
    service, _ = _service(llm)

    service.typing("Расскажи")
    await _settle()
    service.typing("Расскажи про котов")
    await _settle()

    assert [m[-1].text for m in llm.prefills] == ["Расскажи", "Расскажи про котов"]
    assert llm.cancelled == 1
    llm.release.set()


async def test_no_prefill_while_turn_is_running() -> None:
    llm = _GatedStreamLLM()
    service, _ = _service(llm)
    await service.handle("Привет", RecordingSink())
    await _settle()

    service.typing("Ещё вопрос")
    await _settle()

    assert llm.prefills == []
    llm.gate.set()
    await service.wait_idle()


async def test_sending_the_message_stops_pending_prefill() -> None:
    llm = _SlowPrefillLLM()
    service, memory = _service(llm)

    service.typing("Привет")
    await _settle()
    await service.handle("Привет", RecordingSink())
    await service.wait_idle()

    assert llm.cancelled == 1
    assert memory.messages[-1] == Message(Role.ASSISTANT, "Ок.")


async def test_failed_prefill_is_silent() -> None:
    llm = _SlowPrefillLLM(fail=True)
    service, _ = _service(llm)

    service.typing("Привет")
    await _settle()

    sink = RecordingSink()
    await service.handle("Привет", sink)
    await service.wait_idle()
    assert sink.shown_text() == "Ок."
