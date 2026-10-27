import pytest

from vtuber.domain import TurnState, TurnStateError, next_state


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (TurnState.IDLE, TurnState.THINKING),
        (TurnState.THINKING, TurnState.SPEAKING),
        (TurnState.THINKING, TurnState.IDLE),
        (TurnState.THINKING, TurnState.CANCELLED),
        (TurnState.SPEAKING, TurnState.IDLE),
        (TurnState.SPEAKING, TurnState.CANCELLED),
        (TurnState.CANCELLED, TurnState.IDLE),
    ],
)
def test_allowed_transitions(current: TurnState, target: TurnState) -> None:
    assert next_state(current, target) is target


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (TurnState.IDLE, TurnState.SPEAKING),
        (TurnState.IDLE, TurnState.CANCELLED),
        (TurnState.SPEAKING, TurnState.THINKING),
        (TurnState.CANCELLED, TurnState.SPEAKING),
        (TurnState.IDLE, TurnState.IDLE),
    ],
)
def test_forbidden_transition_raises(current: TurnState, target: TurnState) -> None:
    with pytest.raises(TurnStateError, match=f"{current.value}.*{target.value}"):
        next_state(current, target)
