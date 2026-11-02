"""Распознавание faster-whisper (CTranslate2, ADR-0016); модель грузится один раз в `async with`.

faster-whisper и numpy импортируются только при загрузке: пакет `adapters.stt` импортируется и без
группы `stt`, а ядро без голосового ввода запускается.
"""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path  # noqa: TC003 — pydantic разрешает аннотацию поля конфига в рантайме
from typing import TYPE_CHECKING, Literal, Protocol, Self

from pydantic import Field

from vtuber.domain import AudioChunk, GenerationFailed, STTUnavailable
from vtuber.kernel import ConfigSection

if TYPE_CHECKING:
    from collections.abc import Iterable
    from types import TracebackType

    import numpy as np
    import numpy.typing as npt

MODEL_FILE = "model.bin"
# Полная шкала int16 → float [-1, 1).
PCM_SCALE = 32768.0
SAMPLE_RATE = 16_000
# Первый прогон медленнее — платим при загрузке, а не на первой фразе (T-06).
WARMUP_SECONDS = 1


class WhisperConfig(ConfigSection):
    """Секция `[stt.whisper]`.

    `device` — `auto`, `cuda` или `cpu`; `compute_type` — квантование (`int8` на CPU,
    `int8_float16` на GPU, `default` — как в модели). `final_beam` — ширина поиска финальной
    гипотезы; промежуточные всегда жадные: они только для прогрева и показа.
    """

    model_dir: Path
    language: str = Field(min_length=2)
    device: Literal["auto", "cuda", "cpu"]
    compute_type: str = Field(min_length=1)
    threads: int = Field(gt=0)
    final_beam: int = Field(gt=0)


class _Segment(Protocol):
    text: str


class _Model(Protocol):
    """То, что нужно от `faster_whisper.WhisperModel`."""

    def transcribe(
        self,
        audio: npt.NDArray[np.float32],
        *,
        language: str,
        beam_size: int,
        condition_on_previous_text: bool,
        without_timestamps: bool,
    ) -> tuple[Iterable[_Segment], object]:
        """Сегменты (ленивый генератор: работа идёт при обходе) и сведения о записи."""
        ...


class WhisperSTT:
    """Реализует STTPort. Модели нет — не падает при старте, отвечает `STTUnavailable`."""

    def __init__(self, cfg: WhisperConfig) -> None:
        self._cfg = cfg
        self._model: _Model | None = None
        self._unavailable = "Whisper не загружена: адаптер используется вне `async with`"
        # Отменённое распознавание дорабатывает в потоке — следующее ждёт его.
        self._lock = threading.Lock()

    async def __aenter__(self) -> Self:
        try:
            self._model = await asyncio.to_thread(self._load)
        except (OSError, RuntimeError, ValueError, ImportError) as error:
            self._unavailable = (
                f"Модель Whisper не загрузилась из {self._cfg.model_dir}: {error}. Файлы — из "
                "deepdml/faster-whisper-large-v3-turbo-ct2 (ADR-0016)"
            )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._model = None

    async def transcribe(self, audio: AudioChunk, *, final: bool) -> str:
        """Текст отрезка; работа — в потоке (R-34)."""
        model = self._model
        if model is None:
            raise STTUnavailable(self._unavailable)
        if audio.format.sample_rate != SAMPLE_RATE:
            msg = f"Whisper ждёт {SAMPLE_RATE} Гц, а не {audio.format.sample_rate}"
            raise ValueError(msg)
        if not audio.pcm:
            return ""
        beam = self._cfg.final_beam if final else 1
        return await asyncio.to_thread(self._run, model, audio.pcm, beam)

    def _load(self) -> _Model:
        # Типов у faster_whisper нет; нужное от модели описано протоколом `_Model`.
        from faster_whisper import WhisperModel  # type: ignore[import-untyped]  # noqa: PLC0415

        if not (self._cfg.model_dir / MODEL_FILE).is_file():
            msg = f"нет файла {self._cfg.model_dir / MODEL_FILE}"
            raise FileNotFoundError(msg)
        model: _Model = WhisperModel(
            str(self._cfg.model_dir),
            device=self._cfg.device,
            compute_type=self._cfg.compute_type,
            cpu_threads=self._cfg.threads,
        )
        self._run(model, bytes(2 * SAMPLE_RATE * WARMUP_SECONDS), 1)
        return model

    def _run(self, model: _Model, pcm: bytes, beam: int) -> str:
        import numpy as np  # noqa: PLC0415 — см. модуль

        samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / PCM_SCALE
        with self._lock:
            try:
                segments, _ = model.transcribe(
                    samples,
                    language=self._cfg.language,
                    beam_size=beam,
                    condition_on_previous_text=False,
                    without_timestamps=True,
                )
                return " ".join(segment.text.strip() for segment in segments).strip()
            except RuntimeError as exc:
                msg = f"Whisper сорвалась на отрезке: {exc}"
                raise GenerationFailed(msg) from exc
