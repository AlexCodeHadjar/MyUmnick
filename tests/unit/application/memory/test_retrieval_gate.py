"""Гейт поиска и подсказки хода (S-10.5, T-12): память ищется только там, где нужна."""

from datetime import UTC, datetime

import pytest

from tests.fakes import FakeClock, FakeEmbedder, FakeLLM, FakeMemoryStore, RecordingSink
from vtuber.application.conversation import ConversationService
from vtuber.application.memory import (
    FACTS_PREFIX,
    MemoryRecall,
    RecallSearch,
    RetrievalConfig,
    ShortTermMemory,
    is_factual_question,
    needs_memory,
)
from vtuber.application.pipeline import ReplyPipeline
from vtuber.application.prompting import ContextBudget, ContextConfig, PromptBuilder
from vtuber.domain import EmbedKind, Fact, FactSource, Persona, Role
from vtuber.kernel import EventBus, Telemetry
from vtuber.ports import GenerationParams

WHEN = datetime(2026, 11, 2, tzinfo=UTC)
CFG = RetrievalConfig(limit=3, min_score=0.45, timeout_ms=1000, factual_temperature=0.3)
PERSONA = Persona(name="Мика", language="русский", description="", speech_style="", rules=())
BUDGET = ContextBudget(
    ContextConfig(
        max_history_tokens=10_000, trim_ratio=0.5, chars_per_token=3, message_overhead_tokens=4
    )
)


@pytest.mark.parametrize(
    "text",
    [
        "Как меня зовут?",
        "Ты помнишь, что я рассказывал про кота?",
        "Где я живу?",
        "Что я люблю есть на завтрак?",
        "Напомни, о чём мы говорили в прошлый раз",
        "Какой у меня любимый цвет?",
        "Расскажи, что ты знаешь обо мне",
    ],
)
def test_questions_about_user_or_past_open_the_gate(text: str) -> None:
    assert needs_memory(text)


@pytest.mark.parametrize(
    "text",
    [
        "Привет!",
        "Какая столица Японии?",
        "Расскажи анекдот",
        "Как дела?",
        "Я сегодня устал.",
        "Сколько будет два плюс два?",
    ],
)
def test_other_replies_keep_the_gate_closed(text: str) -> None:
    assert not needs_memory(text)


def test_factual_question_is_about_the_world_not_the_user() -> None:
    assert is_factual_question("Какая столица Японии?")
    assert is_factual_question("Когда началась Вторая мировая война?")
    assert not is_factual_question("Как меня зовут?")
    assert not is_factual_question("Где я живу?")
    assert not is_factual_question("Расскажи анекдот")


async def _recall(*facts: str) -> tuple[MemoryRecall, FakeEmbedder]:
    embedder, store = FakeEmbedder(), FakeMemoryStore()
    for text in facts:
        (vector,) = await embedder.embed([text], EmbedKind.PASSAGE)
        await store.add(Fact(text, FactSource.EXTRACTED, 0.5, WHEN), vector)
    embedder.calls.clear()
    return MemoryRecall(
        RecallSearch(embedder, store), CFG, Telemetry(EventBus(), FakeClock())
    ), embedder


async def test_closed_gate_does_not_touch_the_embedder() -> None:
    recall, embedder = await _recall("Пользователя зовут Алексей")

    hints = await recall.hints("Расскажи анекдот")

    assert hints.context == ()
    assert hints.temperature is None
    assert embedder.calls == []


async def test_open_gate_returns_close_facts_as_context() -> None:
    recall, embedder = await _recall(
        "Пользователя зовут Алексей", "Сегодня на ужин пицца с грибами"
    )

    hints = await recall.hints("Как зовут пользователя, как меня зовут?")

    assert hints.context == (f"{FACTS_PREFIX} Пользователя зовут Алексей",)
    assert embedder.calls[0][1] is EmbedKind.QUERY


async def test_factual_question_lowers_temperature() -> None:
    recall, _ = await _recall()

    assert (await recall.hints("Какая столица Японии?")).temperature == CFG.factual_temperature


async def test_memory_failure_does_not_stop_the_turn() -> None:
    embedder, store = FakeEmbedder(available=False), FakeMemoryStore()
    recall = MemoryRecall(RecallSearch(embedder, store), CFG, Telemetry(EventBus(), FakeClock()))

    assert (await recall.hints("Как меня зовут?")).context == ()


async def test_turn_gets_facts_in_user_message_and_keeps_history_clean() -> None:
    llm = FakeLLM("Тебя зовут Алексей.")
    bus = EventBus()
    history = ShortTermMemory(BUDGET)
    pipeline = ReplyPipeline(
        llm, GenerationParams(max_tokens=32, temperature=0.7), Telemetry(bus, FakeClock())
    )
    service = ConversationService(pipeline, PromptBuilder(PERSONA), history, bus)
    recall, _ = await _recall("Пользователя зовут Алексей")
    service.use_memory(recall.hints)

    await service.handle("Как меня зовут? Как зовут пользователя", RecordingSink())
    await service.wait_idle()

    messages, params = llm.calls[0]
    assert messages[-1].role is Role.USER
    assert messages[-1].text.startswith("Как меня зовут? Как зовут пользователя\n(Справка")
    assert "Пользователя зовут Алексей" in messages[-1].text
    assert params.temperature == 0.7
    # В истории — реплика как есть: справка не копится и не ломает префикс следующего хода.
    assert history.messages[0].text == "Как меня зовут? Как зовут пользователя"


@pytest.mark.parametrize(
    "text",
    [
        "Как зовут мою сестру?",
        "Как зовут мою собаку?",
        "Где моя сумка?",
        "О моём брате что скажешь?",
    ],
)
def test_all_forms_of_my_open_the_gate(text: str) -> None:
    # На замере 2026-11-03 без «мою» поиск не шёл вовсе, и модель отвечала «не знаю».
    assert needs_memory(text)
    assert not is_factual_question(text)
