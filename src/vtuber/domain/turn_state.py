"""Жизненный цикл хода: состояния и разрешённые переходы между ними."""

from enum import StrEnum
from types import MappingProxyType
from typing import Final

from vtuber.domain.errors import TurnStateError


class TurnState(StrEnum):
    """Где сейчас ход: ждём реплику, думаем, говорим, прерваны."""

    IDLE = "idle"
    THINKING = "thinking"
    SPEAKING = "speaking"
    CANCELLED = "cancelled"


_ALLOWED: Final = MappingProxyType(
    {
        TurnState.IDLE: frozenset({TurnState.THINKING}),
        # THINKING → IDLE: модель вернула пустой ответ — говорить нечего.
        TurnState.THINKING: frozenset({TurnState.SPEAKING, TurnState.IDLE, TurnState.CANCELLED}),
        TurnState.SPEAKING: frozenset({TurnState.IDLE, TurnState.CANCELLED}),
        TurnState.CANCELLED: frozenset({TurnState.IDLE}),
    }
)


def next_state(current: TurnState, target: TurnState) -> TurnState:
    """Возвращает `target`, если переход из `current` разрешён.

    Raises:
        TurnStateError: переход не разрешён — ошибка в логике сервиса хода.

    """
    if target not in _ALLOWED[current]:
        msg = f"Недопустимый переход хода: {current.value} → {target.value}"
        raise TurnStateError(msg)
    return target
