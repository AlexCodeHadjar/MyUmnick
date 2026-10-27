import asyncio
import time
from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass, field

from tests.fakes import FakeClock, FakeLLM, RecordingSink
from vtuber.application.conversation import ConversationService
from vtuber.application.memory import INTERRUPTED_MARK, ShortTermMemory
from vtuber.application.pipeline import ReplyPipeline
from vtuber.application.prompting import ContextBudget, ContextConfig, PromptBuilder
from vtuber.domain import (
    CancelReason,
    LLMUnavailable,
    Message,
    Persona,
    Role,
    TurnCancelled,
    TurnFinished,
    TurnStarted,
    TurnState,
)
from vtuber.kernel import EventBus, Telemetry
from vtuber.ports import GenerationParams, LLMPort

CANCEL_LIMIT_S = 0.1
PERSONA = Persona(name="Мика", language="русский", description="", speech_style="", rules=())
BUDGET = ContextBudget(
    ContextConfig(
        max_history_tokens=10_000, trim_ratio=0.5, chars_per_token=3, message_overhead_tokens=4
    )
)
type TurnEvent = TurnStarted | TurnFinished | TurnCancelled


@dataclass(slots=True)
class _GatedLLM:
    """Каждый ответ: первая порция, затем ждёт `release` (новое событие на каждый вызов)."""

    first: str = "<happy>Жила-"
    calls: int = 0
    waiting: asyncio.Event = field(default_factory=asyncio.Event)
    release: asyncio.Event = field(default_factory=asyncio.Event)

    async def stream(
        self, messages: Sequence[Message], params: GenerationParams
    ) -> AsyncGenerator[str]:
        self.calls += 1
        yield self.first
        self.waiting.set()
        await self.release.wait()
        yield "была"

    async def prefill(self, messages: Sequence[Message]) -> None:
        """Не нужен в этих тестах."""


@dataclass(slots=True)
class _World:
    service: ConversationService
    memory: ShortTermMemory
    bus: EventBus
    events: list[TurnEvent]


def _world(llm: LLMPort) -> _World:
    bus, events = EventBus(), list[TurnEvent]()

    async def record(event: TurnEvent) -> None:
        events.append(event)

    bus.subscribe(TurnStarted, record)
    bus.subscribe(TurnFinished, record)
    bus.subscribe(TurnCancelled, record)
    memory = ShortTermMemory(BUDGET)
    pipeline = ReplyPipeline(
        llm, GenerationParams(max_tokens=32, temperature=0.5), Telemetry(bus, FakeClock())
    )
    service = ConversationService(pipeline, PromptBuilder(PERSONA), memory, bus)
    return _World(service, memory, bus, events)


def _state(world: _World) -> TurnState:
    """Свежее чтение: mypy иначе сужает тип свойства между проверками."""
    return world.service.state


async def test_full_turn_streams_reply_stores_it_and_publishes_lifecycle() -> None:
    world, sink = _world(FakeLLM("<happy>Привет!")), RecordingSink()

    turn_id = await world.service.handle("Привет", sink)
    await world.service.wait_idle()

    assert sink.shown_text() == "Привет!"
    assert sink.kinds()[-1] == "done"
    assert world.events == [TurnStarted(turn_id), TurnFinished(turn_id)]
    assert world.memory.messages == (
        Message(Role.USER, "Привет"),
        Message(Role.ASSISTANT, "<happy>Привет!"),
    )
    assert _state(world) is TurnState.IDLE


async def test_next_prompt_contains_previous_turns() -> None:
    llm = FakeLLM("Ок.")
    world = _world(llm)

    for text in ("Раз", "Два"):
        await world.service.handle(text, RecordingSink())
        await world.service.wait_idle()

    last_prompt, _ = llm.calls[-1]
    assert [m.text for m in last_prompt[1:]] == ["Раз", "Ок.", "Два"]


async def test_turn_started_is_published_before_the_llm_is_asked() -> None:
    llm = FakeLLM("Ок.")
    world = _world(llm)
    calls_at_start: list[int] = []

    async def remember(_: TurnStarted) -> None:
        calls_at_start.append(len(llm.calls))

    world.bus.subscribe(TurnStarted, remember)
    await world.service.handle("Привет", RecordingSink())
    await world.service.wait_idle()

    assert calls_at_start == [0]


async def test_new_message_interrupts_current_turn_and_keeps_shown_part() -> None:
    llm = _GatedLLM()
    world = _world(llm)
    first_id = await world.service.handle("Расскажи сказку", RecordingSink())
    await llm.waiting.wait()

    llm.release.set()  # второй ответ пройдёт без остановки
    second_id = await world.service.handle("Стоп, другое", RecordingSink())
    await world.service.wait_idle()

    assert TurnCancelled(first_id, CancelReason.NEW_MESSAGE) in world.events
    assert world.events[-1] == TurnFinished(second_id)
    assert world.memory.messages[:2] == (
        Message(Role.USER, "Расскажи сказку"),
        Message(Role.ASSISTANT, f"<happy>Жила-{INTERRUPTED_MARK}"),
    )


async def test_stop_cancels_within_100_ms() -> None:
    llm = _GatedLLM()
    world = _world(llm)
    turn_id = await world.service.handle("Расскажи", RecordingSink())
    await llm.waiting.wait()

    started = time.perf_counter()
    assert await world.service.cancel(CancelReason.USER_STOP)
    assert time.perf_counter() - started <= CANCEL_LIMIT_S

    assert world.events[-1] == TurnCancelled(turn_id, CancelReason.USER_STOP)
    assert _state(world) is TurnState.IDLE


async def test_cancel_when_idle_does_nothing() -> None:
    world = _world(FakeLLM("Ок."))

    assert not await world.service.cancel(CancelReason.USER_STOP)
    assert world.events == []


async def test_unavailable_llm_ends_turn_with_error_and_service_keeps_working() -> None:
    world = _world(FakeLLM("Ок.", fail_after=0))

    turn_id = await world.service.handle("Привет", RecordingSink())
    await world.service.wait_idle()

    [_, cancelled] = world.events
    assert isinstance(cancelled, TurnCancelled)
    assert cancelled.turn_id == turn_id
    assert cancelled.reason is CancelReason.ERROR
    assert "FakeLLM" in cancelled.message
    assert world.memory.messages == ()
    assert _state(world) is TurnState.IDLE


async def test_unexpected_bug_in_sink_is_contained() -> None:
    class _BrokenSink(RecordingSink):
        async def text(self, delta: str) -> None:
            raise RuntimeError("bug")

    world = _world(FakeLLM("Привет"))

    await world.service.handle("Привет", _BrokenSink())
    await world.service.wait_idle()

    assert isinstance(world.events[-1], TurnCancelled)
    assert world.events[-1].reason is CancelReason.ERROR
    assert _state(world) is TurnState.IDLE


async def test_state_follows_the_turn() -> None:
    llm = _GatedLLM()
    world = _world(llm)

    await world.service.handle("Привет", RecordingSink())
    await llm.waiting.wait()
    assert _state(world) is TurnState.SPEAKING

    llm.release.set()
    await world.service.wait_idle()
    assert _state(world) is TurnState.IDLE


async def test_llm_unavailable_message_is_kept_for_the_user() -> None:
    world = _world(FakeLLM("Ок.", fail_after=0, error_type=LLMUnavailable))

    await world.service.handle("Привет", RecordingSink())
    await world.service.wait_idle()

    assert isinstance(world.events[-1], TurnCancelled)
    assert world.events[-1].message


async def test_wait_idle_without_turns_returns_at_once() -> None:
    world = _world(FakeLLM("Ок."))

    await asyncio.wait_for(world.service.wait_idle(), timeout=1)
