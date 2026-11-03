"""Получатель ответа, замечающий его первый вывод: с него ход «говорит», а не «думает»."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from vtuber.domain import AudioChunk, Emotion, Gesture
from vtuber.ports import ReplySink


@dataclass(slots=True)
class FirstOutputSink:
    """Пропускает всё в `inner`; на первом выводе ответа зовёт `on_first` (THINKING → SPEAKING)."""

    inner: ReplySink
    on_first: Callable[[], None]
    on_audio: Callable[[AudioChunk], None]
    on_emotion: Callable[[Emotion], Awaitable[None]]
    started: bool = False

    async def text(self, delta: str) -> None:
        """Первый текст тоже считается выводом."""
        self._mark()
        await self.inner.text(delta)

    async def emotion(self, emotion: Emotion) -> None:
        """Эмоция — и получателю, и на шину."""
        self._mark()
        await self.inner.emotion(emotion)
        await self.on_emotion(emotion)

    async def gesture(self, gesture: Gesture) -> None:
        """Жест — не вывод для замера первого символа: он только добавка к речи."""
        await self.inner.gesture(gesture)

    async def audio(self, chunk: AudioChunk) -> None:
        """Звук — вывод; его длительность нужна для расчёта конца речи."""
        self._mark()
        self.on_audio(chunk)
        await self.inner.audio(chunk)

    async def done(self) -> None:
        """Конец ответа."""
        await self.inner.done()

    def _mark(self) -> None:
        if not self.started:
            self.started = True
            self.on_first()
