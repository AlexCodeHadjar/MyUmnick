"""Голос на отдельном сервере (ADR-0031): фраза уходит по HTTP, PCM приходит одним ответом.

Движку нужны Linux и своя версия torch (FlashInfer), поэтому он живёт в своём процессе:
на арендованной машине через SSH-туннель или в WSL2 на целевой. Для ядра это один и тот же адрес.
"""

import asyncio
from collections.abc import AsyncGenerator
from types import TracebackType
from typing import Final, Self

import httpx
from pydantic import Field

from vtuber.domain import (
    SAMPLE_WIDTH_BYTES,
    AudioChunk,
    AudioFormat,
    GenerationFailed,
    TTSUnavailable,
)
from vtuber.kernel import ConfigSection

MS_PER_S = 1000
HTTP_OK = 200
# Туннель переподключается за пару секунд: один неудачный миг на старте не должен менять голос.
CHECK_ATTEMPTS = 3
CHECK_PAUSE_S = 1.5
UNREACHABLE: Final = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)


class VoiceServerConfig(ConfigSection):
    """Подсекция `[tts.voice_server]`.

    `sample_rate` объявлена здесь, чтобы формат был известен до ответа сервера, и сверяется
    с ним при подключении.
    """

    base_url: str = Field(min_length=1)
    connect_timeout_s: float = Field(gt=0)
    read_timeout_s: float = Field(gt=0)
    sample_rate: int = Field(gt=0)
    chunk_ms: int = Field(gt=0)


class VoiceServerTTS:
    """Реализует TTSPort поверх `scripts/voice_server.py`.

    Сервер недоступен — старт не падает, синтез отвечает `TTSUnavailable`. Состояние не
    запоминается: туннель переподключился, и следующая фраза снова звучит.
    `transport` — подмена транспорта httpx (тесты).
    """

    def __init__(
        self,
        cfg: VoiceServerConfig,
        transport: httpx.AsyncBaseTransport | None = None,
        check_pause_s: float = CHECK_PAUSE_S,
    ) -> None:
        self._cfg = cfg
        self._check_pause_s = check_pause_s
        self._client = httpx.AsyncClient(
            base_url=cfg.base_url,
            timeout=httpx.Timeout(cfg.read_timeout_s, connect=cfg.connect_timeout_s),
            transport=transport,
        )
        self._problem: str | None = (
            "сервер голоса не проверен: адаптер используется вне `async with`"
        )

    async def __aenter__(self) -> Self:
        for attempt in range(CHECK_ATTEMPTS):
            if attempt:
                await asyncio.sleep(self._check_pause_s)
            self._problem = await self._check()
            if self._problem is None:
                break
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self._client.aclose()

    @property
    def problem(self) -> str | None:
        """Почему сервер не готов по проверке при подключении; `None` — готов."""
        return self._problem

    @property
    def audio_format(self) -> AudioFormat:
        """PCM s16le с частотой из конфига."""
        return AudioFormat(self._cfg.sample_rate)

    async def synthesize(self, phrase: str) -> AsyncGenerator[AudioChunk]:
        """Фраза синтезируется на сервере целиком и уходит фрагментами по `chunk_ms`."""
        text = phrase.strip()
        # Без букв говорить нечего («…», «—»): тишина, а не странный звук движка.
        if not any(char.isalpha() for char in text):
            return
        pcm = await self._request_pcm(text)
        step = max(1, self._cfg.sample_rate * self._cfg.chunk_ms // MS_PER_S) * SAMPLE_WIDTH_BYTES
        for start in range(0, len(pcm), step):
            yield AudioChunk(self.audio_format, pcm[start : start + step])
            # Уступка цикла: отмена срабатывает между фрагментами (T-14, контракт TTSPort).
            await asyncio.sleep(0)

    async def _check(self) -> str | None:
        try:
            response = await self._client.get("/health")
            rate = response.json()["sample_rate"] if response.status_code == HTTP_OK else None
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            return f"сервер голоса {self._cfg.base_url} не отвечает: {error!r}"
        if rate != self._cfg.sample_rate:
            return (
                f"сервер голоса отдаёт {rate} Гц, а в конфиге {self._cfg.sample_rate}: "
                "исправьте `[tts.voice_server] sample_rate`"
            )
        return None

    async def _request_pcm(self, text: str) -> bytes:
        try:
            response = await self._client.post("/synthesize", json={"text": text})
        except UNREACHABLE as error:
            msg = f"сервер голоса {self._cfg.base_url} не отвечает: {error!r}"
            raise TTSUnavailable(msg) from error
        except httpx.HTTPError as error:
            msg = f"сервер голоса не синтезировал фразу «{text[:40]}»: {error!r}"
            raise GenerationFailed(msg) from error
        if response.status_code != HTTP_OK:
            msg = f"сервер голоса ответил {response.status_code} на фразу «{text[:40]}»"
            raise GenerationFailed(msg)
        pcm = response.content
        return pcm[: len(pcm) - len(pcm) % SAMPLE_WIDTH_BYTES]
