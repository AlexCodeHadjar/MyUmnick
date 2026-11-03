"""Что именно поднимает наблюдатель (S-17.1): сборка компонентов для `Supervisor`."""

from collections.abc import Awaitable, Callable
from contextlib import aclosing
from dataclasses import dataclass
from types import TracebackType
from typing import Protocol, Self

from vtuber.adapters.llm import LlamaServerProcess
from vtuber.application.pipeline import FillerBank
from vtuber.application.supervision import FailureFlag, WatchedTTS
from vtuber.bootstrap.config import AppConfig
from vtuber.bootstrap.container import Backends, TTSAdapter, tts_backends
from vtuber.domain import Component, LLMUnavailable
from vtuber.ports import LLMPort, TTSPort

VOICE_PROBE = "Готова."


class LlmSupervised:
    """Сервер, запущенный ядром; внешний не наблюдается: поднять его ядро всё равно не может."""

    component = Component.LLM

    def __init__(
        self, server: LlamaServerProcess, warm: Callable[[], Awaitable[str | None]]
    ) -> None:
        self._server = server
        self._warm = warm

    async def healthy(self) -> bool:
        """Процесс жив и отвечает; модели нет (до мастера) — следить не за чем."""
        return await self._server.healthy()

    async def restart(self) -> None:
        """Новый процесс и прогрев: кэш промпта умер вместе со старым (T-06)."""
        await self._server.restart()
        if (problem := await self._warm()) is not None:
            raise LLMUnavailable(problem)


class ReloadableTTS(TTSPort, Protocol):
    """Движок голоса, который загружается и выгружается контекстом."""

    async def __aenter__(self) -> Self:
        """Загрузить модель."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Выгрузить модель."""
        ...


class TtsSupervised:
    """Голос: сбой виден по флагу, поднять — значит загрузить модель заново и проверить её."""

    component = Component.TTS

    def __init__(self, tts: ReloadableTTS, flag: FailureFlag) -> None:
        self._tts = tts
        self._flag = flag

    async def healthy(self) -> bool:
        """Сбоя не было."""
        return not self._flag.failed

    async def restart(self) -> None:
        """Перезагрузка и пробная фраза.

        Raises:
            TTSUnavailable: модель так и не отвечает.

        """
        await self._tts.__aexit__(None, None, None)
        await self._tts.__aenter__()
        async with aclosing(self._tts.synthesize(VOICE_PROBE)) as audio:
            async for _ in audio:
                pass
        self._flag.clear()


@dataclass(frozen=True, slots=True)
class VoiceParts:
    """Голос шлюза: движок (грузится при старте), его междометия и обёртка для наблюдателя."""

    tts: TTSAdapter
    fillers: FillerBank
    watched: WatchedTTS
    flag: FailureFlag


def build_voice(cfg: AppConfig) -> VoiceParts | None:
    """Голос из конфига; `none` — без голоса."""
    tts = tts_backends().create(cfg.tts.backend, cfg.tts)
    if tts is None:
        return None
    flag = FailureFlag()
    watched = WatchedTTS(tts, flag, cfg.supervisor.voice_timeout_s)
    return VoiceParts(tts, FillerBank(cfg.pipeline.filler), watched, flag)


def with_voice(llm: LLMPort, voice: VoiceParts | None) -> Backends:
    """Движки хода: конвейер получает обёртку, чтобы сбой голоса был замечен."""
    if voice is None:
        return Backends(llm, None, None)
    return Backends(llm, voice.watched, voice.fillers)
