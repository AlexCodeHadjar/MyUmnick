"""Краткосрочная память: история текущего разговора, только дописывание и усечение блоком."""

from collections import deque
from dataclasses import dataclass
from itertools import chain
from typing import Final

from vtuber.application.prompting import ContextBudget
from vtuber.domain import Message, Role, Turn

INTERRUPTED_MARK: Final = "…"
"""Конец прерванного ответа. Нейтральный знак, а не «[прервано]»: модель повторяет пометки."""


@dataclass(frozen=True, slots=True)
class _StoredTurn:
    messages: tuple[Message, Message]
    tokens: int


class ShortTermMemory:
    """История ходов для промпта (T-04).

    Пока история в бюджете, она только дописывается — префикс промпта не меняется, KV-кэш
    живёт. Превысила — старшие ходы отрезаются сразу до `trim_target`, поэтому кэш сбрасывается
    раз в много ходов, а не каждый ход. Режутся целые ходы: чередование user/assistant не
    ломается. Самый новый ход не отрезается никогда.
    """

    def __init__(self, budget: ContextBudget) -> None:
        self._budget = budget
        self._turns: deque[_StoredTurn] = deque()
        self._tokens = 0

    @property
    def messages(self) -> tuple[Message, ...]:
        """История в порядке ходов: user, assistant, user, assistant и так далее."""
        return tuple(chain.from_iterable(turn.messages for turn in self._turns))

    @property
    def tokens(self) -> int:
        """Оценка токенов всей истории."""
        return self._tokens

    def append(self, turn: Turn) -> tuple[Message, ...]:
        """Дописывает ход; при превышении бюджета отрезает старший блок.

        Returns:
            Отрезанные сообщения (пусто, если усечения не было) — для резюме в простое (T-13).

        """
        messages = _as_messages(turn)
        self._turns.append(_StoredTurn(messages, self._budget.tokens(messages)))
        self._tokens += self._turns[-1].tokens
        if self._tokens <= self._budget.max_history_tokens:
            return ()
        return self._trim()

    def _trim(self) -> tuple[Message, ...]:
        dropped: list[Message] = []
        while len(self._turns) > 1 and self._tokens > self._budget.trim_target:
            oldest = self._turns.popleft()
            self._tokens -= oldest.tokens
            dropped.extend(oldest.messages)
        return tuple(dropped)


def _as_messages(turn: Turn) -> tuple[Message, Message]:
    reply = f"{turn.reply_text}{INTERRUPTED_MARK}" if turn.is_interrupted else turn.reply_text
    return Message(Role.USER, turn.user_text), Message(Role.ASSISTANT, reply)
