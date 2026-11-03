"""Реплика извне: сообщение зрителя из чата стрима или другого источника (FR-14)."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IncomingMessage:
    """Реплика из источника `source` (например, `twitch`) от автора `author`.

    `is_viewer` — текст пишет посторонний и он идёт как данные (FR-31). Свои источники плагинов, чей
    текст задаёт сам ведущий (таймер), ставят False.
    """

    source: str
    author: str
    text: str
    is_viewer: bool = True
