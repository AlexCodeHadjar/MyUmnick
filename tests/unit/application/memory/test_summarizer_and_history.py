"""Резюме отрезанной истории (S-10.4, T-04) и его место в истории промпта."""

import pytest

from tests.fakes import FakeLLM
from vtuber.application.memory import MAX_SUMMARY_CHARS, ShortTermMemory, Summarizer
from vtuber.application.prompting import ContextBudget, ContextConfig
from vtuber.domain import GenerationFailed, Message, Role, Turn, TurnId
from vtuber.ports import GenerationParams

PARAMS = GenerationParams(max_tokens=300, temperature=0.2)
DROPPED = (Message(Role.USER, "Я Алексей"), Message(Role.ASSISTANT, "<happy>Привет, Алексей!"))
BUDGET = ContextBudget(
    ContextConfig(
        max_history_tokens=100, trim_ratio=0.5, chars_per_token=1, message_overhead_tokens=0
    )
)


async def test_summary_folds_previous_one_and_strips_tags() -> None:
    llm = FakeLLM("  Пользователь   Алексей представился.\n")

    summary = await Summarizer(llm, PARAMS).summarize("Говорили о котах.", DROPPED)

    assert summary == "Пользователь Алексей представился."
    request = llm.calls[0][0][1].text
    assert "Прежнее резюме: Говорили о котах." in request
    assert "Ассистент: Привет, Алексей!" in request


async def test_long_summary_is_clipped_at_sentence_end() -> None:
    llm = FakeLLM("Очень длинное предложение пересказа. " * 80)

    summary = await Summarizer(llm, PARAMS).summarize(None, DROPPED)

    assert len(summary) <= MAX_SUMMARY_CHARS
    assert summary.endswith(".")


async def test_empty_summary_is_generation_failed() -> None:
    with pytest.raises(GenerationFailed):
        await Summarizer(FakeLLM("   "), PARAMS).summarize(None, DROPPED)


def test_summary_goes_into_first_user_message_and_keeps_alternation() -> None:
    history = ShortTermMemory(BUDGET)
    history.append(Turn(TurnId(1), "Как дела?", "Отлично!"))
    before = history.messages

    history.set_summary("Пользователь Алексей из Казани.")

    first, *rest = history.messages
    assert first.role is Role.USER
    assert first.text == "(Кратко о начале разговора: Пользователь Алексей из Казани.)\nКак дела?"
    assert tuple(rest) == before[1:]
    assert history.summary == "Пользователь Алексей из Казани."


def test_empty_history_ignores_summary() -> None:
    history = ShortTermMemory(BUDGET)
    history.set_summary("что-то")

    assert history.messages == ()
