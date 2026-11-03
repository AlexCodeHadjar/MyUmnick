import io
from pathlib import Path

from tests.fakes import FakeLLM
from tools.eval_emotion import EmotionCase, judge, main, render, run_cases
from tools.jsonl import read_jsonl
from vtuber.application.prompting import PromptBuilder
from vtuber.bootstrap import load_persona
from vtuber.domain import Emotion
from vtuber.ports import GenerationParams

ROOT = Path(__file__).resolve().parents[2]
CASE = EmotionCase(id="sad-01", text="У меня умер кот.", fits=(Emotion.SAD,))


def test_fitting_tag_at_the_start_passes() -> None:
    result = judge(CASE, "<sad>Мне очень жаль.")

    assert result.tagged
    assert result.fitting
    assert result.shown == "Мне очень жаль."
    assert result.leaked == ()


def test_missing_wrong_or_late_tag_does_not_fit() -> None:
    assert not judge(CASE, "Мне очень жаль.").tagged
    assert not judge(CASE, "<happy>Ура!").fitting
    late = judge(CASE, "Мне жаль. <sad>Правда.")
    assert not late.tagged
    assert not late.fitting


def test_closing_tag_does_not_reach_text_or_speech() -> None:
    result = judge(CASE, "<thinking>Жаль</thought>, правда.</sad>")
    assert result.leaked == ()
    assert result.shown == "Жаль, правда."


def test_report_counts_and_lists_failures() -> None:
    report = render([judge(CASE, "<sad>Жаль."), judge(CASE, "Без тега.")])

    assert "с тегом в начале: 1 (50 %)" in report
    assert "x sad-01" in report


async def test_each_case_is_a_separate_conversation_with_real_persona() -> None:
    llm = FakeLLM("<sad>Жаль.")
    prompts = PromptBuilder(load_persona(ROOT / "personas" / "default.toml"))
    params = GenerationParams(max_tokens=16, temperature=0.7)

    results = await run_cases(llm, prompts, [CASE, CASE], params)

    assert [r.fitting for r in results] == [True, True]
    first, second = (messages for messages, _ in llm.calls)
    assert first == second
    assert first[-1].text == CASE.text


def test_repository_set_has_thirty_varied_cases() -> None:
    cases = read_jsonl(ROOT / "eval" / "emotion_ru.jsonl", EmotionCase)

    assert len(cases) == 30
    assert len({case.id for case in cases}) == 30
    assert {emotion for case in cases for emotion in case.fits} >= {
        Emotion.HAPPY,
        Emotion.SAD,
        Emotion.ANGRY,
        Emotion.SURPRISED,
        Emotion.EMBARRASSED,
        Emotion.THINKING,
    }


def test_cli_reports_unavailable_server_with_exit_code_2(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    cases.write_text(CASE.model_dump_json() + "\n", encoding="utf-8")
    output = io.StringIO()
    env = {"VTUBER_LLM__BASE_URL": "http://127.0.0.1:9", "VTUBER_LLM__CONNECT_TIMEOUT_S": "0.2"}

    assert main(["--cases", str(cases)], env, output) == 2


def test_leak_check_still_sees_bracket_markup() -> None:
    assert judge(CASE, "<sad>Жаль [think], правда.").leaked == ("[think]",)
