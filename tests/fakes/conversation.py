"""Сборка ConversationService на фейках — для тестов шлюза и терминала."""

from vtuber.application.conversation import ConversationService
from vtuber.application.memory import ShortTermMemory
from vtuber.application.pipeline import ReplyPipeline
from vtuber.application.prompting import ContextBudget, ContextConfig, PromptBuilder
from vtuber.domain import Persona
from vtuber.kernel import EventBus, Telemetry
from vtuber.ports import GenerationParams, LLMPort

TEST_PERSONA = Persona(name="Мика", language="русский", description="", speech_style="", rules=())


def make_conversation(llm: LLMPort, bus: EventBus, telemetry: Telemetry) -> ConversationService:
    """Сервис хода с персоной-заглушкой и щедрым бюджетом истории."""
    budget = ContextBudget(
        ContextConfig(
            max_history_tokens=10_000, trim_ratio=0.5, chars_per_token=3, message_overhead_tokens=4
        )
    )
    pipeline = ReplyPipeline(llm, GenerationParams(max_tokens=32, temperature=0.5), telemetry)
    return ConversationService(pipeline, PromptBuilder(TEST_PERSONA), ShortTermMemory(budget), bus)
