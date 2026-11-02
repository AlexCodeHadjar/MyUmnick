import asyncio
import io
from collections import Counter
from pathlib import Path

import pytest

from tests.fakes import FakeLLM
from tests.llm_stub import LLMStub
from tools.eval_quality import (
    EvalCase,
    Expect,
    evaluate,
    load_cases,
    main,
    render,
    run_case,
)
from vtuber.domain import Role
from vtuber.ports import GenerationParams

ROOT = Path(__file__).resolve().parents[2]
PARAMS = GenerationParams(max_tokens=64, temperature=0.2)


def test_any_of_matches_word_starts_so_inflections_pass() -> None:
    expect = Expect(any_of=["Толст"])

    assert evaluate(expect, "Это написал Лев Толстой.") == []
    assert evaluate(expect, "Роман Толстого.") == []
    assert evaluate(expect, "Это не Достоевский.") != []


def test_any_of_ignores_case_and_yo() -> None:
    assert evaluate(Expect(any_of=["зелен"]), "Твой любимый цвет — ЗЕЛЁНЫЙ!") == []


def test_numbers_do_not_match_longer_numbers() -> None:
    assert evaluate(Expect(any_of=["8"]), "Планет восемь, то есть 8.") == []
    assert evaluate(Expect(any_of=["8"]), "Их 80.") != []


def test_none_of_fails_on_forbidden_word() -> None:
    assert evaluate(Expect(none_of=["Сатурн"]), "Самая большая — Сатурн.") != []


@pytest.mark.parametrize(
    ("reply", "is_refusal"),
    [
        ("Хм, я не знаю, ты мне не рассказывал.", True),
        ("Понятия не имею!", True),
        ("Ты ел пиццу.", False),
    ],
)
def test_refusal_is_recognised(reply: str, is_refusal: bool) -> None:
    assert (evaluate(Expect(refusal=True), reply) == []) is is_refusal


def test_sentence_limit() -> None:
    expect = Expect(max_sentences=2)

    assert evaluate(expect, "Привет! Как дела?") == []
    assert evaluate(expect, "Раз. Два. Три.") != []


@pytest.mark.parametrize("reply", ["**Жирно**", "# Заголовок", "- пункт", "1. пункт", "Ура 🎉"])
def test_markdown_and_emoji_are_flagged(reply: str) -> None:
    assert evaluate(Expect(no_markdown=True), reply) != []


def test_cyrillic_ratio() -> None:
    assert evaluate(Expect(min_cyrillic_ratio=0.9), "Осень — золотая пора.") == []
    assert evaluate(Expect(min_cyrillic_ratio=0.9), "Autumn is a golden season.") != []


def test_emotion_tags_are_stripped_before_checks() -> None:
    assert evaluate(Expect(no_markdown=True, max_sentences=1), "<happy>Привет!") == []


async def test_multi_turn_case_keeps_history_and_checks_last_reply() -> None:
    llm = FakeLLM("Тебя зовут Саша.")
    case = EvalCase(
        id="mem-1",
        kind="memory",
        turns=["Меня зовут Саша.", "Как меня зовут?"],
        expect=Expect(any_of=["Саш"]),
    )

    result = await run_case(llm, case, PARAMS)

    assert result.passed
    last_messages, _ = llm.calls[-1]
    assert [message.role for message in last_messages] == [
        Role.SYSTEM,
        Role.USER,
        Role.ASSISTANT,
        Role.USER,
    ]


def test_report_groups_results_by_kind() -> None:
    results = [("knowledge", True), ("knowledge", False), ("honesty", True)]
    totals = Counter(kind for kind, _ in results)

    table = render(totals, Counter(kind for kind, ok in results if ok))

    assert "knowledge" in table
    assert "1/2" in table
    assert "2/3" in table


def test_repository_eval_set_is_valid() -> None:
    cases = load_cases(ROOT / "eval" / "qa_ru.jsonl")

    assert len(cases) == 150
    assert len({case.id for case in cases}) == 150
    assert {case.kind for case in cases} == {"knowledge", "honesty", "persona", "memory", "russian"}


async def test_cli_runs_eval_against_stub(tmp_path: Path) -> None:
    cases = tmp_path / "cases.jsonl"
    cases.write_text(
        '{"id": "k1", "kind": "knowledge", "turns": ["Столица Японии?"], '
        '"expect": {"any_of": ["Токио"]}}\n',
        encoding="utf-8",
    )
    output = io.StringIO()

    async with LLMStub("Это Токио.", chunk_size=4, delay_s=0) as stub:
        env = {"VTUBER_LLM__BASE_URL": stub.url}
        code = await asyncio.to_thread(main, ["--cases", str(cases)], env, output)

    assert code == 0
    assert "knowledge" in output.getvalue()
    assert "1/1" in output.getvalue()
