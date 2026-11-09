"""Kokoro-82M (ADR-0034): английский голос ONNX через `kokoro-onnx`, синтез фразы в потоке.

Веса — Apache-2.0; фонемизатор espeak-ng — GPL-3.0, как у Piper (ADR-0013): приложение
не распространяется.
"""

import asyncio
import threading
from collections.abc import AsyncGenerator, Callable
from pathlib import Path
from types import TracebackType
from typing import Protocol, Self

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
SAMPLE_RATE = 24000  # у Kokoro одна частота
PCM_MAX = 32767
# Первый синтез ONNX Runtime готовит граф — платим при загрузке, а не на первой реплике (T-06).
WARMUP_PHRASE = "Hello."
MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0"


class KokoroConfig(ConfigSection):
    """Подсекция `[tts.kokoro]`.

    `voice` — голос из `voices_path` (`af_heart`, `af_bella`, `bf_emma`…); `lang` — язык
    фонемизатора (`en-us`, `en-gb`); `speed` — темп (1 — обычный).
    """

    model_path: Path
    voices_path: Path
    voice: str = Field(min_length=1)
    lang: str = Field(min_length=2)
    speed: float = Field(gt=0)
    chunk_ms: int = Field(gt=0)


class KokoroLike(Protocol):
    """То, что нужно от `kokoro_onnx.Kokoro`: синтез фразы в float-сэмплы."""

    def create(self, text: str, voice: str, speed: float, lang: str) -> tuple[object, int]:
        """(сэмплы float32 в [-1, 1], частота)."""
        ...


type KokoroLoader = Callable[[Path, Path], KokoroLike]


def load_kokoro(model: Path, voices: Path) -> KokoroLike:
    """Модель Kokoro и банк голосов."""
    for path in (model, voices):
        if not path.is_file():
            raise FileNotFoundError(path)
    from kokoro_onnx import Kokoro  # noqa: PLC0415 — пакет из группы `kokoro`, грузится по делу

    engine: KokoroLike = Kokoro(str(model), str(voices))
    return engine


def to_pcm16(samples: object) -> bytes:
    """float32-сэмплы → PCM s16le."""
    import numpy as np  # noqa: PLC0415 — numpy приходит с группой `kokoro`

    array = np.clip(np.asarray(samples, dtype=np.float32), -1.0, 1.0)
    return (array * PCM_MAX).astype("<i2").tobytes()


class KokoroTTS:
    """Реализует TTSPort; модель грузится и прогревается один раз в `async with` (R-40).

    Модели нет или голос неизвестен — старт не падает, синтез отвечает `TTSUnavailable`.
    """

    def __init__(self, cfg: KokoroConfig, loader: KokoroLoader = load_kokoro) -> None:
        self._cfg = cfg
        self._loader = loader
        self._engine: KokoroLike | None = None
        self._unavailable = "Kokoro не загружен: адаптер используется вне `async with`"
        self._lock = threading.Lock()

    async def __aenter__(self) -> Self:
        try:
            self._engine = await asyncio.to_thread(self._load)
        except FileNotFoundError as missing:
            self._unavailable = f"Нет файла Kokoro {missing}: скачайте с {MODEL_URL}"
        # onnxruntime и фонемизатор бросают свои исключения — любое значит «голос не готов» (R-43).
        except Exception as error:  # noqa: BLE001
            self._unavailable = f"Kokoro не загрузился ({self._cfg.model_path}): {error}"
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._engine = None

    @property
    def problem(self) -> str | None:
        """Почему Kokoro не готов; `None` — готов (для `FallbackTTS`)."""
        return None if self._engine is not None else self._unavailable

    @property
    def audio_format(self) -> AudioFormat:
        """PCM s16le 24 кГц."""
        return AudioFormat(SAMPLE_RATE)

    async def synthesize(self, phrase: str) -> AsyncGenerator[AudioChunk]:
        """Фраза синтезируется в потоке и уходит фрагментами по `chunk_ms`."""
        engine = self._engine
        if engine is None:
            raise TTSUnavailable(self._unavailable)
        text = phrase.strip()
        if not any(char.isalpha() for char in text):
            return
        pcm = await asyncio.to_thread(self._synthesize_pcm, engine, text)
        step = max(1, SAMPLE_RATE * self._cfg.chunk_ms // MS_PER_S) * SAMPLE_WIDTH_BYTES
        for start in range(0, len(pcm), step):
            yield AudioChunk(self.audio_format, pcm[start : start + step])
            await asyncio.sleep(0)  # отмена — между фрагментами (T-14, контракт TTSPort)

    def _load(self) -> KokoroLike:
        engine = self._loader(self._cfg.model_path, self._cfg.voices_path)
        self._synthesize_pcm(engine, WARMUP_PHRASE)
        return engine

    def _synthesize_pcm(self, engine: KokoroLike, text: str) -> bytes:
        cfg = self._cfg
        with self._lock:
            try:
                samples, rate = engine.create(text, voice=cfg.voice, speed=cfg.speed, lang=cfg.lang)
            except Exception as error:
                msg = f"Kokoro не синтезировал фразу «{text[:40]}»: {error}"
                raise GenerationFailed(msg) from error
        if rate != SAMPLE_RATE:
            msg = f"Kokoro вернул {rate} Гц вместо {SAMPLE_RATE}"
            raise GenerationFailed(msg)
        return to_pcm16(samples)
