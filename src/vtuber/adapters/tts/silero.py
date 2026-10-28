"""Silero TTS (ADR-0012): модель `torch.package` на CPU, синтез фразы целиком в потоке.

torch импортируется только при работе с моделью: пакет `adapters.tts` (и движок Piper) должен
импортироваться и без группы `silero`, а запуск ядра — не ждать загрузки torch.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncGenerator, Callable
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol, Self

from pydantic import Field

from vtuber.domain import (
    SAMPLE_WIDTH_BYTES,
    AudioChunk,
    AudioFormat,
    GenerationFailed,
    TTSUnavailable,
)
from vtuber.kernel import ConfigSection

if TYPE_CHECKING:
    from types import TracebackType

    import torch

MS_PER_S = 1000
# Полная шкала int16: float [-1, 1] → s16le.
PCM_SCALE = 32767
# Первый синтез заметно медленнее — платим при загрузке, а не на первой реплике (T-06).
WARMUP_PHRASE = "Привет."


class SileroConfig(ConfigSection):
    """Подсекция `[tts.silero]`.

    `threads` — потоки CPU для torch (процесс-глобально: torch в ядре только у TTS);
    `chunk_ms` — размер фрагментов, которыми готовая фраза уходит в UI.
    """

    model_path: Path
    speaker: str = Field(min_length=1)
    sample_rate: Literal[8000, 24000, 48000]
    threads: int = Field(gt=0)
    chunk_ms: int = Field(gt=0)


class SileroModel(Protocol):
    """То, что нужно от модели Silero (`TTSModelMultiAcc`): синтез фразы в тензор float."""

    def apply_tts(self, *, text: str, speaker: str, sample_rate: int) -> torch.Tensor:
        """Синтез всей фразы: моно, float [-1, 1], частота `sample_rate`."""
        ...


type ModelLoader = Callable[[Path], SileroModel]


def load_package(path: Path) -> SileroModel:
    """Модель из `.pt`-пакета Silero (официальный способ загрузки без torch.hub)."""
    from torch.package.package_importer import PackageImporter  # noqa: PLC0415 — см. модуль

    model: SileroModel = PackageImporter(path).load_pickle("tts_models", "model")
    return model


def to_pcm(audio: torch.Tensor) -> bytes:
    """Тензор float [-1, 1] → PCM s16le; выход за шкалу обрезается, а не переворачивается."""
    import torch  # noqa: PLC0415 — см. модуль

    samples = (audio.clamp(-1.0, 1.0) * PCM_SCALE).round().to(torch.int16)
    return samples.numpy().astype("<i2", copy=False).tobytes()


class SileroTTS:
    """Реализует TTSPort; модель грузится один раз в `async with` (R-40).

    Модели нет или она не читается — адаптер не падает при старте, а отвечает `TTSUnavailable`
    на синтез: так статус TTS виден в UI, как у LLM.
    """

    def __init__(self, cfg: SileroConfig, loader: ModelLoader = load_package) -> None:
        self._cfg = cfg
        self._loader = loader
        self._model: SileroModel | None = None
        self._unavailable = "Silero не загружена: адаптер используется вне `async with`"
        # Отменённый синтез дорабатывает в своём потоке — следующий ждёт его, а не мешает.
        self._lock = threading.Lock()

    async def __aenter__(self) -> Self:
        try:
            self._model = await asyncio.to_thread(self._load)
        except FileNotFoundError:
            self._unavailable = (
                f"Нет модели Silero {self._cfg.model_path}: скачайте "
                "https://models.silero.ai/models/tts/ru/v5_6_ru.pt (ADR-0012)"
            )
        except (OSError, RuntimeError, ValueError, ImportError) as error:
            self._unavailable = f"Модель Silero не загрузилась ({self._cfg.model_path}): {error}"
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._model = None

    @property
    def audio_format(self) -> AudioFormat:
        """PCM s16le с частотой из конфига: 8, 24 или 48 кГц."""
        return AudioFormat(self._cfg.sample_rate)

    async def synthesize(self, phrase: str) -> AsyncGenerator[AudioChunk]:
        """Фраза синтезируется целиком в потоке и уходит фрагментами по `chunk_ms`."""
        model = self._model
        if model is None:
            raise TTSUnavailable(self._unavailable)
        text = phrase.strip()
        # Без букв говорить нечего («…», «—»): Silero на таком падает, а ответ — тишина.
        if not any(char.isalpha() for char in text):
            return
        pcm = await asyncio.to_thread(self._synthesize_pcm, model, text)
        step = self._chunk_bytes()
        for start in range(0, len(pcm), step):
            yield AudioChunk(self.audio_format, pcm[start : start + step])
            # Фрагменты готовы сразу — без уступки цикла потребитель проглотил бы их все до того,
            # как сработает отмена (T-14; контракт TTSPort это проверяет).
            await asyncio.sleep(0)

    def _load(self) -> SileroModel:
        import torch  # noqa: PLC0415 — см. модуль

        torch.set_num_threads(self._cfg.threads)
        model = self._loader(self._cfg.model_path)
        self._synthesize_pcm(model, WARMUP_PHRASE)
        return model

    def _synthesize_pcm(self, model: SileroModel, text: str) -> bytes:
        cfg = self._cfg
        with self._lock:
            try:
                audio = model.apply_tts(text=text, speaker=cfg.speaker, sample_rate=cfg.sample_rate)
            except (RuntimeError, ValueError, KeyError, IndexError) as error:
                msg = f"Silero не синтезировала фразу «{text[:40]}»: {error}"
                raise GenerationFailed(msg) from error
        return to_pcm(audio)

    def _chunk_bytes(self) -> int:
        samples = max(1, self._cfg.sample_rate * self._cfg.chunk_ms // MS_PER_S)
        return samples * SAMPLE_WIDTH_BYTES
