"""Выбор голоса при старте (ADR-0031): сервер голоса не готов — говорит запасной движок."""

from collections.abc import AsyncGenerator
from contextlib import aclosing
from types import TracebackType
from typing import Protocol, Self

import structlog

from vtuber.domain import AudioChunk, AudioFormat
from vtuber.ports import TTSPort

_log = structlog.get_logger()


class CheckedTTS(TTSPort, Protocol):
    """Основной движок: контекстный менеджер, который умеет сказать, почему он не готов."""

    @property
    def problem(self) -> str | None:
        """Причина неготовности; `None` — готов."""
        ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...


class ManagedTTS(TTSPort, Protocol):
    """Запасной движок: загружается только тогда, когда он понадобился."""

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...


class FallbackTTS:
    """Реализует TTSPort: движок выбирается один раз при старте.

    Посреди работы движок не меняется: у них разные голоса и частоты, а временный обрыв
    туннеля виден как `TTSUnavailable` и проходит сам со следующей фразы.
    """

    def __init__(self, primary: CheckedTTS, fallback: ManagedTTS) -> None:
        self._primary = primary
        self._fallback = fallback
        self._active: TTSPort = primary
        self._fallback_entered = False

    async def __aenter__(self) -> Self:
        await self._primary.__aenter__()
        problem = self._primary.problem
        if problem is not None:
            _log.warning("tts.fallback", problem=problem)
            self._active = await self._fallback.__aenter__()
            self._fallback_entered = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._fallback_entered:
            await self._fallback.__aexit__(exc_type, exc, tb)
        await self._primary.__aexit__(exc_type, exc, tb)

    @property
    def audio_format(self) -> AudioFormat:
        """Формат движка, выбранного при старте."""
        return self._active.audio_format

    async def synthesize(self, phrase: str) -> AsyncGenerator[AudioChunk]:
        """Фраза идёт в выбранный движок."""
        async with aclosing(self._active.synthesize(phrase)) as stream:
            async for chunk in stream:
                yield chunk
