"""Сервис хода сообщает фоновой памяти о записанном ходе и отрезанной истории (S-10.4)."""

from tests.fakes import FakeClock, FakeLLM, RecordingSink
from vtuber.application.conversation import ConversationService
from vtuber.application.memory import ShortTermMemory
from vtuber.application.pipeline import ReplyPipeline
from vtuber.application.prompting import ContextBudget, ContextConfig, PromptBuilder
from vtuber.domain import Message, Persona, Role, Turn, TurnRemembered
from vtuber.kernel import EventBus, Telemetry
from vtuber.ports import GenerationParams

PERSONA = Persona(name="Мика", language="русский", description="", speech_style="", rules=())
# Токены = символы; лимит — на один ход «Раз/Ок.» с запасом: второй ход вытеснит первый.
TINY = ContextBudget(
    ContextConfig(
        max_history_tokens=8, trim_ratio=0.5, chars_per_token=1, message_overhead_tokens=0
    )
)


async def test_each_turn_is_published_with_what_was_trimmed() -> None:
    bus, events = EventBus(), list[TurnRemembered]()

    async def record(event: TurnRemembered) -> None:
        events.append(event)

    bus.subscribe(TurnRemembered, record)
    pipeline = ReplyPipeline(
        FakeLLM("Ок."), GenerationParams(max_tokens=8, temperature=0.5), Telemetry(bus, FakeClock())
    )
    service = ConversationService(pipeline, PromptBuilder(PERSONA), ShortTermMemory(TINY), bus)

    for text in ("Раз", "Два"):
        await service.handle(text, RecordingSink())
        await service.wait_idle()

    first, second = events
    assert first.turn == Turn(first.turn.id, "Раз", "Ок.")
    assert first.dropped == ()
    assert second.turn.user_text == "Два"
    assert second.dropped == (Message(Role.USER, "Раз"), Message(Role.ASSISTANT, "Ок."))
