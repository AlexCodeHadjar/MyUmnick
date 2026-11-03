from pathlib import Path

from tests.fakes import FakeLLM
from tools.eval_gesture import GestureCase, judge, render, run_cases
from tools.jsonl import read_jsonl
from vtuber.application.prompting import PromptBuilder
from vtuber.bootstrap import load_persona
from vtuber.domain import Gesture
from vtuber.ports import GenerationParams

ROOT = Path(__file__).resolve().parents[2]
CASE = GestureCase(id="agree-01", text="Котики милые?", fits=(Gesture.NOD,))


def test_fitting_gesture_passes_and_no_gesture_is_not_a_failure() -> None:
    assert judge(CASE, "<nod>Очень!").fitting
    assert judge(CASE, "Очень!").fitting
    assert not judge(CASE, "<shake>Нет.").fitting


def test_report_counts_gestures_and_lists_failures() -> None:
    report = render([judge(CASE, "<nod>Да."), judge(CASE, "<shake>Нет."), judge(CASE, "Да.")])
    assert "с жестом: 2 (67 %)" in report
    assert "уместных из них: 1 (50 %)" in report
    assert "x agree-01" in report


async def test_prompt_of_the_real_persona_lists_gestures() -> None:
    llm = FakeLLM("<nod>Да.")
    prompts = PromptBuilder(load_persona(ROOT / "personas" / "default.toml"))
    params = GenerationParams(max_tokens=16, temperature=0.7)
    results = await run_cases(llm, prompts, [CASE], params)
    assert results[0].gestures == (Gesture.NOD,)
    assert "<startle>" in llm.calls[0][0][0].text


def test_case_set_is_valid() -> None:
    cases = read_jsonl(ROOT / "eval" / "gesture_ru.jsonl", GestureCase)
    assert len({case.id for case in cases}) == len(cases) >= 16
