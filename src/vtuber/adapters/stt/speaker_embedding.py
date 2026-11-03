"""Отпечаток голоса ERes2Net через sherpa-onnx (ADR-0029); на CPU, GPU остаётся диалогу.

sherpa-onnx и numpy импортируются при первой фразе: пакеты группы `sounds`, без них ядро работает.
"""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path  # noqa: TC003 — pydantic разрешает аннотацию при создании модели
from typing import Final, Protocol

from pydantic import Field

from vtuber.domain import AudioChunk, GenerationFailed, STTUnavailable
from vtuber.kernel import ConfigSection

# Полная шкала int16 → float [-1, 1).
PCM_SCALE: Final = 32768.0


class SpeakerModelConfig(ConfigSection):
    """Секция `[stt.speaker_model]`."""

    model_path: Path
    threads: int = Field(gt=0)


class _Extractor(Protocol):
    """То, что нужно от `sherpa_onnx.SpeakerEmbeddingExtractor`."""

    def create_stream(self) -> object:
        """Новый поток."""
        ...

    def compute(self, stream: object) -> list[float]:
        """Отпечаток; блокирует."""
        ...


class SherpaSpeakerEmbedder:
    """Реализует `SpeakerEmbedderPort`; модель грузится при первой фразе, в своём потоке."""

    def __init__(self, cfg: SpeakerModelConfig) -> None:
        self._cfg = cfg
        self._extractor: _Extractor | None = None
        self._loading = threading.Lock()

    async def embed(self, audio: AudioChunk) -> tuple[float, ...]:
        """Отпечаток фразы; см. `SpeakerEmbedderPort`."""
        return await asyncio.to_thread(self._embed, audio)

    def _embed(self, audio: AudioChunk) -> tuple[float, ...]:
        extractor = self._load()
        import numpy as np  # noqa: PLC0415 — необязательный пакет, см. докстринг модуля

        samples = np.frombuffer(audio.pcm, dtype=np.int16).astype(np.float32) / PCM_SCALE
        stream = extractor.create_stream()
        stream.accept_waveform(audio.format.sample_rate, samples)  # type: ignore[attr-defined]
        stream.input_finished()  # type: ignore[attr-defined]
        if not extractor.is_ready(stream):  # type: ignore[attr-defined]
            msg = "Фраза слишком короткая для отпечатка голоса"
            raise GenerationFailed(msg)
        return tuple(extractor.compute(stream))

    def _load(self) -> _Extractor:
        with self._loading:
            if self._extractor is None:
                self._extractor = self._create()
            return self._extractor

    def _create(self) -> _Extractor:
        try:
            import sherpa_onnx  # type: ignore[import-untyped]  # noqa: PLC0415 — см. докстринг
        except ImportError as exc:
            msg = "Нет пакета sherpa-onnx: uv sync --extra sounds"
            raise STTUnavailable(msg) from exc
        if not self._cfg.model_path.is_file():
            msg = f"Нет модели голоса: {self._cfg.model_path}"
            raise STTUnavailable(msg)
        config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=str(self._cfg.model_path), num_threads=self._cfg.threads
        )
        extractor: _Extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)
        return extractor
