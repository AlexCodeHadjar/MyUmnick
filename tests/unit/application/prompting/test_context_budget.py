import pytest
from pydantic import ValidationError

from vtuber.application.prompting import ContextBudget, ContextConfig
from vtuber.domain import Message, Role


def _config(**overrides: float) -> ContextConfig:
    values: dict[str, float] = {
        "max_history_tokens": 100,
        "trim_ratio": 0.5,
        "chars_per_token": 3.0,
        "message_overhead_tokens": 4,
    }
    return ContextConfig.model_validate(values | overrides)


def test_tokens_are_estimated_from_characters_plus_overhead_per_message() -> None:
    budget = ContextBudget(_config())
    messages = [Message(Role.USER, "a" * 9), Message(Role.ASSISTANT, "b" * 10)]

    assert budget.tokens(messages) == (3 + 4) + (4 + 4)


def test_trim_target_leaves_one_minus_ratio_of_the_limit() -> None:
    assert ContextBudget(_config()).trim_target == 50
    assert ContextBudget(_config(trim_ratio=0.25)).trim_target == 75


@pytest.mark.parametrize(
    "overrides",
    [
        {"trim_ratio": 0.0},
        {"trim_ratio": 1.0},
        {"max_history_tokens": 0},
        {"chars_per_token": 0.0},
        {"message_overhead_tokens": -1},
    ],
)
def test_nonsense_settings_are_rejected(overrides: dict[str, float]) -> None:
    with pytest.raises(ValidationError):
        _config(**overrides)
