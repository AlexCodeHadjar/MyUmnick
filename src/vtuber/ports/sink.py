"""Порт получателя ответа: куда конвейер отдаёт результаты хода (WebSocket, терминал, тест)."""

from typing import Protocol

from vtuber.domain import AudioChunk, Emotion


class ReplySink(Protocol):
    """Получатель результатов одного хода; конвейер не знает, что за ним."""

    async def text(self, delta: str) -> None:
        """Порция текста ответа для показа (без тегов эмоций)."""

    async def emotion(self, emotion: Emotion) -> None:
        """В ответе сменилась эмоция."""

    async def audio(self, chunk: AudioChunk) -> None:
        """Фрагмент речи ответа; приходят по порядку, пока идёт ход (S-7.5)."""

    async def done(self) -> None:
        """Ответ закончен полностью. При отмене или ошибке не вызывается."""
