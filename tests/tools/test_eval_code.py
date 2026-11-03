import json
from pathlib import Path

from tests.fakes import FakeLLM
from tools.eval_code import CodeCase, extract_code, judge, render, run_cases, run_checks
from tools.jsonl import read_jsonl
from vtuber.ports import GenerationParams

ROOT = Path(__file__).resolve().parents[2]
CASE = CodeCase(id="add", task="Write add(a, b).", checks="assert add(1, 2) == 3")
GOOD = "```python\ndef add(a, b):\n    return a + b\n```"
# Эталоны: иначе ошибка в самой проверке выглядела бы как слабость модели.
REFERENCES = ROOT / "tests" / "data" / "code_references.json"


def test_working_code_passes() -> None:
    assert judge(CASE, GOOD).passed


def test_wrong_code_and_syntax_error_fail_with_a_reason() -> None:
    wrong = judge(CASE, "```python\ndef add(a, b):\n    return a - b\n```")
    assert not wrong.passed
    assert "AssertionError" in wrong.problem
    assert not judge(CASE, "```python\ndef add(:\n```").passed


def test_hanging_code_is_stopped() -> None:
    assert "не уложился" in run_checks("while True:\n    pass", "", timeout_s=0.5)


def test_code_block_is_taken_from_the_reply() -> None:
    assert extract_code(f"Sure!\n{GOOD}\nDone.") == "def add(a, b):\n    return a + b\n"
    assert extract_code("x = 1") == "x = 1"


def test_report_lists_failures() -> None:
    report = render([judge(CASE, GOOD), judge(CASE, "```python\nx = 1\n```")])
    assert "прошло: 1 (50 %)" in report
    assert "x add" in report


async def test_each_task_is_asked_separately() -> None:
    llm = FakeLLM(GOOD)
    results = await run_cases(llm, [CASE, CASE], GenerationParams(16, 0.0))
    assert [r.passed for r in results] == [True, True]
    assert len(llm.calls) == 2


def test_every_case_has_a_reference_that_passes_its_checks() -> None:
    cases = read_jsonl(ROOT / "eval" / "code_en.jsonl", CodeCase)
    references = json.loads(REFERENCES.read_text(encoding="utf-8"))
    assert {case.id for case in cases} == set(references)
    for case in cases:
        assert run_checks(references[case.id], case.checks) == "", case.id
