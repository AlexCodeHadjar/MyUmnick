"""Ход без модели (S-18.5): показать готовый звук тем же путём, что и ответ, с той же отменой."""

from collections.abc import AsyncGenerator
from contextlib import aclosing

from vtuber.domain import AudioChunk, Emotion
from vtuber.ports import ReplySink


async def play_performance(title: str, audio: AsyncGenerator[AudioChunk], sink: ReplySink) -> None:
    """Текст и эмоция — сразу, звук — по мере чтения; отмена закрывает источник."""
    await sink.emotion(Emotion.HAPPY)
    await sink.text(f"Пою: {title}")
    async with aclosing(audio) as chunks:
        async for chunk in chunks:
            await sink.audio(chunk)
    await sink.done()
