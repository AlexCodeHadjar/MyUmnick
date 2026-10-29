"""Долговременные факты и фоновая работа памяти (S-10.4): дедупликация, простой, сбои."""

import asyncio
from datetime import UTC, datetime

import pytest

from tests.fakes import FakeClock, FakeEmbedder, FakeLLM, FakeMemoryStore
from vtuber.application.memory import (
    FactExtractor,
    FactMemory,
    FactMemoryConfig,
    MemoryKeeper,
    ShortTermMemory,
    Summarizer,
)
from vtuber.application.prompting import ContextBudget, ContextConfig
from vtuber.application.scheduler import IdleScheduler, SchedulerConfig
from vtuber.domain import (
    EmbedKind,
    FactSource,
    GenerationFailed,
    Message,
    Role,
    Turn,
    TurnFinished,
    TurnId,
    TurnRemembered,
)
from vtuber.kernel import EventBus
from vtuber.ports import GenerationParams

PARAMS = GenerationParams(max_tokens=300, temperature=0.2)
WHEN = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)
FACTS_JSON = (
    '{"facts": [{"text": "Пользователя зовут Алексей", "importance": 1},'
    ' {"text": "Пользователь любит котов", "importance": 0.5},'
    ' {"text": "пользователя зовут Алексей", "importance": 1}]}'
)
TURN = Turn(TurnId(1), "Меня зовут Алексей, обожаю котов", "<happy>Здорово!")
BUDGET = ContextBudget(
    ContextConfig(
        max_history_tokens=10_000, trim_ratio=0.5, chars_per_token=3, message_overhead_tokens=4
    )
)


def _facts(answer: str, store: FakeMemoryStore) -> FactMemory:
    extractor = FactExtractor(FakeLLM(answer), PARAMS)
    return FactMemory(extractor, FakeEmbedder(), store, FactMemoryConfig(dedup_score=0.95))


async def test_learn_stores_unique_facts_with_source_and_time() -> None:
    store = FakeMemoryStore()

    stored = await _facts(FACTS_JSON, store).learn(TURN, WHEN)

    assert stored == 2
    texts = [fact.text for fact, _ in store.facts]
    assert texts == ["Пользователя зовут Алексей", "Пользователь любит котов"]
    assert {(fact.source, fact.created_at) for fact, _ in store.facts} == {
        (FactSource.EXTRACTED, WHEN)
    }


async def test_known_fact_is_not_stored_again() -> None:
    store = FakeMemoryStore()
    memory = _facts(FACTS_JSON, store)

    await memory.learn(TURN, WHEN)
    again = await memory.learn(TURN, WHEN)

    assert again == 0
    assert len(store.facts) == 2


async def test_broken_json_fails_without_touching_the_store() -> None:
    store = FakeMemoryStore()

    with pytest.raises(GenerationFailed):
        await _facts("Пользователя зовут Алексей.", store).learn(TURN, WHEN)
    assert store.facts == []


async def test_no_facts_means_no_embedding() -> None:
    embedder, store = FakeEmbedder(), FakeMemoryStore()
    extractor = FactExtractor(FakeLLM('{"facts": []}'), PARAMS)
    memory = FactMemory(extractor, embedder, store, FactMemoryConfig(dedup_score=0.95))

    assert await memory.learn(TURN, WHEN) == 0
    assert embedder.calls == []


async def test_facts_are_embedded_as_passages() -> None:
    embedder, store = FakeEmbedder(), FakeMemoryStore()
    extractor = FactExtractor(FakeLLM(FACTS_JSON), PARAMS)
    memory = FactMemory(extractor, embedder, store, FactMemoryConfig(dedup_score=0.95))

    await memory.learn(TURN, WHEN)

    assert [kind for _, kind in embedder.calls] == [EmbedKind.PASSAGE]


class _World:
    """Хранитель памяти с планировщиком на FakeClock: простой наступает по сну планировщика."""

    def __init__(
        self, extractor_answer: str, summary_answer: str = "Пользователь Алексей."
    ) -> None:
        self.clock = FakeClock()
        self.bus = EventBus()
        self.store = FakeMemoryStore()
        self.history = ShortTermMemory(BUDGET)
        self.scheduler = IdleScheduler(SchedulerConfig(idle_after_ms=100), self.clock, self._sleep)
        self.scheduler.follow(self.bus)
        keeper = MemoryKeeper(
            self.scheduler,
            self.history,
            Summarizer(FakeLLM(summary_answer), PARAMS),
            _facts(extractor_answer, self.store),
        )
        keeper.now = lambda: WHEN
        keeper.follow(self.bus)

    async def _sleep(self, seconds: float) -> None:
        self.clock.advance_ms(seconds * 1000)
        await asyncio.sleep(0)

    async def turn(self, dropped: tuple[Message, ...] = ()) -> None:
        self.history.append(TURN)
        await self.bus.publish(TurnRemembered(TURN, dropped))
        await self.bus.publish(TurnFinished(TURN.id))
        # FakeLLM отдаёт JSON порциями по 4 символа, каждая — шаг цикла.
        for _ in range(500):
            await asyncio.sleep(0)


async def test_keeper_learns_facts_and_summarizes_dropped_in_idle() -> None:
    world = _World(FACTS_JSON)
    loop = asyncio.create_task(world.scheduler.run())

    await world.turn(dropped=(Message(Role.USER, "Привет"), Message(Role.ASSISTANT, "Привет!")))
    loop.cancel()

    assert world.history.summary == "Пользователь Алексей."
    assert len(world.store.facts) == 2
    assert world.scheduler.pending == 0


async def test_broken_json_does_not_break_the_queue_or_the_summary() -> None:
    world = _World("не JSON вовсе")
    loop = asyncio.create_task(world.scheduler.run())

    await world.turn(dropped=(Message(Role.USER, "Привет"), Message(Role.ASSISTANT, "Привет!")))
    loop.cancel()

    assert world.history.summary == "Пользователь Алексей."
    assert world.store.facts == []
    assert world.scheduler.pending == 0


async def test_turn_without_dropped_history_only_learns_facts() -> None:
    world = _World(FACTS_JSON)
    loop = asyncio.create_task(world.scheduler.run())

    await world.turn()
    loop.cancel()

    assert world.history.summary is None
    assert len(world.store.facts) == 2
