"""Порт получателя ответа: куда конвейер отдаёт результаты хода (WebSocket, терминал, тест)."""

from typing import Protocol

from vtuber.domain import Emotion


class ReplySink(Protocol):
    """Получатель результатов одного хода; конвейер не знает, что за ним.

    `audio` появится вместе с TTS-веткой конвейера (S-7.5).
    """

    async def text(self, delta: str) -> None:
        """Порция текста ответа для показа (без тегов эмоций)."""

    async def emotion(self, emotion: Emotion) -> None:
        """В ответе сменилась эмоция."""

    async def done(self) -> None:
        """Ответ закончен полностью. При отмене или ошибке не вызывается."""
