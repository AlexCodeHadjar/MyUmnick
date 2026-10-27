"""Бюджет контекста: оценка токенов истории и порог блочного усечения (T-04)."""

import math
from collections.abc import Iterable

from pydantic import Field

from vtuber.domain import Message
from vtuber.kernel import ConfigSection


class ContextConfig(ConfigSection):
    """Секция `[context]`.

    `chars_per_token` — сколько символов русского текста в среднем на токен; калибруется по
    настоящему токенизатору модели (S-9.1). `message_overhead_tokens` — служебные токены шаблона
    чата на сообщение (роль, разделители).
    """

    max_history_tokens: int = Field(gt=0)
    trim_ratio: float = Field(gt=0, lt=1)
    chars_per_token: float = Field(gt=0)
    message_overhead_tokens: int = Field(ge=0)


class ContextBudget:
    """Приближённый счёт токенов — без запроса к серверу, чтобы не тормозить горячий путь."""

    def __init__(self, cfg: ContextConfig) -> None:
        self._cfg = cfg

    @property
    def max_history_tokens(self) -> int:
        """Предел истории: превысила — пора усекать."""
        return self._cfg.max_history_tokens

    @property
    def trim_target(self) -> int:
        """До скольких токенов усекать: сразу на долю `trim_ratio`, а не по одному сообщению."""
        return math.floor(self._cfg.max_history_tokens * (1 - self._cfg.trim_ratio))

    def tokens(self, messages: Iterable[Message]) -> int:
        """Оценка токенов сообщений вместе со служебными токенами шаблона."""
        return sum(
            math.ceil(len(message.text) / self._cfg.chars_per_token)
            + self._cfg.message_overhead_tokens
            for message in messages
        )
