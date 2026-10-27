"""Контекст текущего хода: turn_id для логов и метрик через contextvars."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

import structlog

from vtuber.domain import TurnId

_CURRENT_TURN: ContextVar[TurnId | None] = ContextVar("vtuber_current_turn", default=None)


def current_turn() -> TurnId | None:
    """Номер текущего хода или None вне хода; чтение — десятки наносекунд (горячий путь)."""
    return _CURRENT_TURN.get()


@contextmanager
def turn_context(turn_id: TurnId) -> Iterator[None]:
    """Внутри блока ход `turn_id` — текущий для метрик, а логи несут поле `turn_id`.

    Задачи asyncio, созданные в блоке, наследуют ход (копия контекста при создании задачи).
    """
    token = _CURRENT_TURN.set(turn_id)
    try:
        with structlog.contextvars.bound_contextvars(turn_id=turn_id):
            yield
    finally:
        _CURRENT_TURN.reset(token)
