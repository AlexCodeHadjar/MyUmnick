import io
from pathlib import Path

from tests.fakes import FakeEmbedder, FakeLLM, FakeMemoryStore
from tools.eval_checks import Expect
from tools.eval_memory import Engines, MemoryCase, main, render, run_case
from tools.jsonl import read_jsonl
from vtuber.application.prompting import PromptBuilder
from vtuber.bootstrap import load_persona
from vtuber.ports import GenerationParams

ROOT = Path(__file__).resolve().parents[2]
PARAMS = GenerationParams(max_tokens=64, temperature=0.3)
FACTS = '{"facts": [{"text": "Пользователя зовут Олег", "importance": 1}]}'
CASE = MemoryCase(
    id="cross-01",
    say=("Меня зовут Олег.",),
    ask="Как меня зовут?",
    expect=Expect(any_of=("Олег",)),
)


def _engines(answer: str) -> Engines:
    prompts = PromptBuilder(load_persona(ROOT / "personas" / "default.toml"))
    return Engines(FakeLLM(answer, chunk_size=64), FakeEmbedder(), prompts, PARAMS)


async def test_fact_is_stored_in_first_session_and_answer_is_checked_in_second() -> None:
    store = FakeMemoryStore()

    result = await run_case(_engines(FACTS), CASE, store)

    assert result.stored == 1
    assert [fact.text for fact, _ in store.facts] == ["Пользователя зовут Олег"]
    assert result.passed


async def test_broken_extraction_is_counted_not_fatal() -> None:
    result = await run_case(_engines("Просто ответ без JSON"), CASE, FakeMemoryStore())

    assert result.stored == 0
    assert result.extraction_failures == 1
    assert not result.passed
    assert "x cross-01" in render([result])


def test_repository_set_loads() -> None:
    cases = read_jsonl(ROOT / "eval" / "memory_ru.jsonl", MemoryCase)

    assert len(cases) == 20
    assert all(case.expect.any_of for case in cases)


def test_cli_reports_unavailable_server(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    cases.write_text(CASE.model_dump_json() + "\n", encoding="utf-8")
    env = {"VTUBER_LLM__BASE_URL": "http://127.0.0.1:9", "VTUBER_LLM__CONNECT_TIMEOUT_S": "0.2"}

    assert main(["--cases", str(cases)], env, io.StringIO()) == 2
