"""Метки звуков от SenseVoice через sherpa-onnx (ADR-0027); нужна только метка, текст не берём.

Выложенная модель не знает русского, поэтому её текст здесь бессмыслен. sherpa-onnx и numpy
импортируются только при загрузке: пакеты из группы `sounds`, без них ядро запускается.
"""

from __future__ import annotations

import asyncio
from pathlib import Path  # noqa: TC003 — pydantic разрешает аннотацию при создании модели
from typing import TYPE_CHECKING, Final, Protocol, Self

from pydantic import Field

from vtuber.domain import AudioChunk, GenerationFailed, SoundKind, STTUnavailable
from vtuber.kernel import ConfigSection

if TYPE_CHECKING:
    from types import TracebackType

# Полная шкала int16 → float [-1, 1).
PCM_SCALE: Final = 32768.0
_SOUNDS: Final = {
    "<|Laughter|>": SoundKind.LAUGHTER,
    "<|Applause|>": SoundKind.APPLAUSE,
    "<|Cough|>": SoundKind.COUGH,
    "<|Sneeze|>": SoundKind.SNEEZE,
    "<|Cry|>": SoundKind.CRY,
    "<|BGM|>": SoundKind.MUSIC,
}


class SenseVoiceConfig(ConfigSection):
    """Секция `[stt.sound_model]`: работает на CPU, GPU остаётся диалогу."""

    model_path: Path
    tokens_path: Path
    threads: int = Field(gt=0)
    timeout_s: float = Field(gt=0)


def sound_of(tag: str) -> SoundKind | None:
    """Метка модели → звук; речь, дыхание и неизвестное — не звук для реакции."""
    return _SOUNDS.get(tag)


class _Recognizer(Protocol):
    """То, что нужно от `sherpa_onnx.OfflineRecognizer`."""

    def create_stream(self) -> object:
        """Новый поток разбора."""
        ...

    def decode_stream(self, stream: object) -> None:
        """Разобрать звук потока; блокирует."""
        ...


class SenseVoiceSounds:
    """Реализует `SoundClassifierPort`; модель живёт столько же, сколько контекст."""

    def __init__(self, cfg: SenseVoiceConfig) -> None:
        self._cfg = cfg
        self._recognizer: _Recognizer | None = None

    async def __aenter__(self) -> Self:
        self._recognizer = await asyncio.to_thread(self._load)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._recognizer = None

    async def classify(self, audio: AudioChunk) -> SoundKind | None:
        """Звук окна; см. `SoundClassifierPort`."""
        recognizer = self._recognizer
        if recognizer is None:
            msg = "SenseVoice не загружена"
            raise STTUnavailable(msg)
        try:
            async with asyncio.timeout(self._cfg.timeout_s):
                tag = await asyncio.to_thread(_decode, recognizer, audio)
        except TimeoutError as exc:
            msg = f"SenseVoice не уложилась в {self._cfg.timeout_s} с"
            raise GenerationFailed(msg) from exc
        return sound_of(tag)

    def _load(self) -> _Recognizer:
        try:
            import sherpa_onnx  # type: ignore[import-untyped]  # noqa: PLC0415 — см. докстринг
        except ImportError as exc:
            msg = "Нет пакета sherpa-onnx: uv sync --extra sounds"
            raise STTUnavailable(msg) from exc
        if not self._cfg.model_path.is_file() or not self._cfg.tokens_path.is_file():
            msg = f"Нет модели SenseVoice: {self._cfg.model_path}"
            raise STTUnavailable(msg)
        recognizer: _Recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=str(self._cfg.model_path),
            tokens=str(self._cfg.tokens_path),
            num_threads=self._cfg.threads,
            language="auto",
            use_itn=False,
        )
        return recognizer


def _decode(recognizer: _Recognizer, audio: AudioChunk) -> str:
    import numpy as np  # noqa: PLC0415 — необязательный пакет, см. докстринг модуля

    samples = np.frombuffer(audio.pcm, dtype=np.int16).astype(np.float32) / PCM_SCALE
    stream = recognizer.create_stream()
    stream.accept_waveform(audio.format.sample_rate, samples)  # type: ignore[attr-defined]
    recognizer.decode_stream(stream)
    event: str = stream.result.event  # type: ignore[attr-defined]
    return event
