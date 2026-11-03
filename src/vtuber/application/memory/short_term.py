"""Краткосрочная память: история текущего разговора, только дописывание и усечение блоком."""

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import chain
from typing import Final

from vtuber.application.prompting import ContextBudget
from vtuber.domain import Message, Role, Turn

INTERRUPTED_MARK: Final = "…"
"""Конец прерванного ответа. Нейтральный знак, а не «[прервано]»: модель повторяет пометки."""
SUMMARY_TEMPLATE: Final = "(Кратко о начале разговора: {summary})\n{text}"
"""Резюме — в первой реплике истории, а не отдельным системным сообщением: не все шаблоны чата
допускают system не в начале, а чередование user/assistant так не ломается."""


@dataclass(frozen=True, slots=True)
class _StoredTurn:
    messages: tuple[Message, Message]
    tokens: int


class ShortTermMemory:
    """История ходов для промпта (T-04).

    Пока история в бюджете, она только дописывается — префикс промпта не меняется, KV-кэш
    живёт. Превысила — старшие ходы отрезаются сразу до `trim_target`, поэтому кэш сбрасывается
    раз в много ходов, а не каждый ход. Режутся целые ходы: чередование user/assistant не
    ломается. Самый новый ход не отрезается никогда. Отрезанное сжимает в резюме фоновая
    память (`Summarizer`); резюме идёт в начало истории и меняется так же редко.
    """

    def __init__(self, budget: ContextBudget) -> None:
        self._budget = budget
        self._turns: deque[_StoredTurn] = deque()
        self._tokens = 0
        self._summary: str | None = None

    @property
    def messages(self) -> tuple[Message, ...]:
        """История в порядке ходов: user, assistant, …; резюме — в первой реплике (T-04)."""
        messages = tuple(chain.from_iterable(turn.messages for turn in self._turns))
        if self._summary is None or not messages:
            return messages
        first = SUMMARY_TEMPLATE.format(summary=self._summary, text=messages[0].text)
        return (Message(Role.USER, first), *messages[1:])

    @property
    def summary(self) -> str | None:
        """Резюме отрезанной части разговора; None — ничего не отрезано или ещё не сжато."""
        return self._summary

    def set_summary(self, summary: str) -> None:
        """Новое резюме (вбирает прежнее) — от фоновой памяти в простое."""
        self._summary = summary

    @property
    def tokens(self) -> int:
        """Оценка токенов всей истории."""
        return self._tokens

    def restore(self, turns: Sequence[Turn], summary: str | None) -> None:
        """Разговор прошлого запуска (ADR-0020); лишнее по бюджету отрезается как обычно."""
        self._summary = summary
        for turn in turns:
            self.append(turn)

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
