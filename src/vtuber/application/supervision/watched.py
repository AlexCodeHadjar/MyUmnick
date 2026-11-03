"""Голос и слух работают в процессе ядра: о сбое узнаём по их ответам, а не отдельной проверкой.

Пробный синтез раз в секунды отнимал бы CPU у ответа. Обёртки только замечают `*Unavailable` и
зависание и поднимают флаг; остальное делает наблюдатель.
"""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import aclosing

from vtuber.domain import AudioChunk, AudioFormat, STTUnavailable, TTSUnavailable
from vtuber.ports import STTPort, TTSPort


class FailureFlag:
    """Сбой замечен, но ещё не исправлен."""

    def __init__(self) -> None:
        self._failed = False

    @property
    def failed(self) -> bool:
        """Есть ли необработанный сбой."""
        return self._failed

    def fail(self) -> None:
        """Отметить сбой."""
        self._failed = True

    def clear(self) -> None:
        """Компонент поднят заново."""
        self._failed = False


class WatchedTTS:
    """`TTSPort`: движок молчит дольше `timeout_s` или недоступен — флаг и `TTSUnavailable`.

    Зависший поток остановить нельзя, но ход не будет ждать его: текст ответа уже показан.
    """

    def __init__(self, inner: TTSPort, flag: FailureFlag, timeout_s: float) -> None:
        self._inner = inner
        self._flag = flag
        self._timeout_s = timeout_s

    @property
    def audio_format(self) -> AudioFormat:
        """Формат внутреннего движка."""
        return self._inner.audio_format

    async def synthesize(self, phrase: str) -> AsyncGenerator[AudioChunk]:
        """Фрагменты внутреннего движка с ограничением на ожидание каждого."""
        async with aclosing(self._inner.synthesize(phrase)) as audio:
            while True:
                try:
                    async with asyncio.timeout(self._timeout_s):
                        chunk = await anext(audio)
                except StopAsyncIteration:
                    return
                except TimeoutError as exc:
                    self._flag.fail()
                    msg = f"Голос не ответил за {self._timeout_s} с"
                    raise TTSUnavailable(msg) from exc
                except TTSUnavailable:
                    self._flag.fail()
                    raise
                yield chunk


class WatchedSTT:
    """`STTPort`: то же для распознавания; срок большой, на CPU длинная фраза идёт секунды."""

    def __init__(self, inner: STTPort, flag: FailureFlag, timeout_s: float) -> None:
        self._inner = inner
        self._flag = flag
        self._timeout_s = timeout_s

    async def transcribe(self, audio: AudioChunk, *, final: bool) -> str:
        """Текст фразы от внутреннего движка."""
        try:
            async with asyncio.timeout(self._timeout_s):
                return await self._inner.transcribe(audio, final=final)
        except TimeoutError as exc:
            self._flag.fail()
            msg = f"Распознавание не ответило за {self._timeout_s} с"
            raise STTUnavailable(msg) from exc
        except STTUnavailable:
            self._flag.fail()
            raise
