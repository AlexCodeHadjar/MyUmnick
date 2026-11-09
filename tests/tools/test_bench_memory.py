from pathlib import Path

from tests.fakes import FakeClock, FakeEmbedder, FakeLLM, FakeMemoryStore
from tools.bench_memory import Timing, first_token_ms, seed, summarize
from vtuber.application.memory import MemoryRecall, RecallSearch, RetrievalConfig
from vtuber.application.prompting import PromptBuilder
from vtuber.bootstrap import load_persona
from vtuber.kernel import EventBus, Telemetry

ROOT = Path(__file__).resolve().parents[2]
CFG = RetrievalConfig(limit=3, min_score=0.01, timeout_ms=1000, factual_temperature=0.3)


async def test_with_memory_prompt_carries_found_facts() -> None:
    llm, embedder, store = FakeLLM("Ок."), FakeEmbedder(), FakeMemoryStore()
    await seed(store, embedder, 8)
    prompts = PromptBuilder(load_persona(ROOT / "personas" / "default.toml"))
    recall = MemoryRecall(RecallSearch(embedder, store), CFG, Telemetry(EventBus(), FakeClock()))

    assert await first_token_ms(llm, prompts, "Как меня зовут?", None) >= 0
    assert await first_token_ms(llm, prompts, "Как меня зовут?", recall) >= 0

    (plain, _), (with_memory, _) = llm.calls
    assert plain[-1].text == "Как меня зовут?"
    assert "Справка" in with_memory[-1].text


def test_summary_covers_both_series() -> None:
    summary = summarize([Timing("a", 10.0, 20.0), Timing("b", 30.0, 40.0)])

    assert summary["Без памяти, мс"].max == 30
    assert summary["С памятью, мс"].p50 == 20
