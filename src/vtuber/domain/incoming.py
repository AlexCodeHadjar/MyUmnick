"""Реплика извне: сообщение зрителя из чата стрима или другого источника (FR-14)."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IncomingMessage:
    """Реплика из источника `source` (например, `twitch`) от автора `author`."""

    source: str
    author: str
    text: str
