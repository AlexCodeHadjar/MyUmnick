"""Детектор речи Silero VAD v5 в ONNX (ADR-0016): окно 32 мс, около миллисекунды на CPU.

Модель принимает окно с контекстом из 64 прошлых сэмплов и своё состояние — так же, как обёртка
`OnnxWrapper` в пакете silero-vad. onnxruntime и numpy импортируются только при загрузке.
"""

from __future__ import annotations

import asyncio
from pathlib import Path  # noqa: TC003 — pydantic разрешает аннотацию поля конфига в рантайме
from typing import TYPE_CHECKING, Final, Protocol, Self

from pydantic import Field

from vtuber.domain import SAMPLE_WIDTH_BYTES, AudioFormat, STTUnavailable
from vtuber.kernel import ConfigSection

if TYPE_CHECKING:
    from types import TracebackType

    import numpy as np
    import numpy.typing as npt

SAMPLE_RATE: Final = 16_000
WINDOW_SAMPLES: Final = 512
CONTEXT_SAMPLES: Final = 64
STATE_SHAPE: Final = (2, 1, 128)
PCM_SCALE: Final = 32768.0


class VadConfig(ConfigSection):
    """Секция `[stt.vad]`: файл модели и потоки CPU (1 — окно короткое, больше не нужно)."""

    model_path: Path
    threads: int = Field(gt=0)


class _Session(Protocol):
    def run(
        self, output_names: None, input_feed: dict[str, npt.NDArray[np.float32 | np.int64]]
    ) -> list[npt.NDArray[np.float32]]:
        """Выходы по порядку: вероятность и новое состояние."""
        ...


class SileroVad:
    """Реализует VadPort. Модели нет — отвечает `STTUnavailable`, не падает при старте."""

    def __init__(self, cfg: VadConfig) -> None:
        self._cfg = cfg
        self._session: _Session | None = None
        self._state: npt.NDArray[np.float32] | None = None
        self._context: npt.NDArray[np.float32] | None = None
        self._unavailable = "Silero VAD не загружен: адаптер используется вне `async with`"

    async def __aenter__(self) -> Self:
        try:
            self._session = await asyncio.to_thread(self._load)
            self.reset()
        except (OSError, RuntimeError, ValueError, ImportError) as error:
            self._unavailable = f"Silero VAD не загрузился ({self._cfg.model_path}): {error}"
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._session = None

    @property
    def audio_format(self) -> AudioFormat:
        """16 кГц: на неё рассчитаны окно и контекст."""
        return AudioFormat(SAMPLE_RATE)

    @property
    def window_samples(self) -> int:
        """512 сэмплов = 32 мс."""
        return WINDOW_SAMPLES

    async def speech_probability(self, pcm: bytes) -> float:
        """Вероятность речи в окне; вызовы идут по одному — у модели есть состояние."""
        session = self._session
        if session is None:
            raise STTUnavailable(self._unavailable)
        if len(pcm) != WINDOW_SAMPLES * SAMPLE_WIDTH_BYTES:
            msg = f"окно VAD — {WINDOW_SAMPLES} сэмплов, получено байт: {len(pcm)}"
            raise ValueError(msg)
        return await asyncio.to_thread(self._step, session, pcm)

    def reset(self) -> None:
        """Обнулить состояние и контекст."""
        import numpy as np  # noqa: PLC0415 — см. модуль

        self._state = np.zeros(STATE_SHAPE, dtype=np.float32)
        self._context = np.zeros((1, CONTEXT_SAMPLES), dtype=np.float32)

    def _load(self) -> _Session:
        # Типов у onnxruntime нет; нужное от сессии описано протоколом `_Session`.
        import onnxruntime as ort  # type: ignore[import-untyped]  # noqa: PLC0415 — см. модуль

        if not self._cfg.model_path.is_file():
            msg = f"нет файла {self._cfg.model_path}"
            raise FileNotFoundError(msg)
        options = ort.SessionOptions()
        options.intra_op_num_threads = self._cfg.threads
        options.inter_op_num_threads = 1
        session: _Session = ort.InferenceSession(
            str(self._cfg.model_path), options, providers=["CPUExecutionProvider"]
        )
        return session

    def _step(self, session: _Session, pcm: bytes) -> float:
        import numpy as np  # noqa: PLC0415 — см. модуль

        window = np.frombuffer(pcm, dtype="<i2").astype(np.float32).reshape(1, -1) / PCM_SCALE
        context = self._context
        state = self._state
        if context is None or state is None:
            raise STTUnavailable(self._unavailable)
        joined = np.concatenate([context, window], axis=1)
        output, new_state = session.run(
            None,
            {"input": joined, "state": state, "sr": np.array(SAMPLE_RATE, dtype=np.int64)},
        )
        self._state = new_state
        self._context = joined[:, -CONTEXT_SAMPLES:]
        return float(output.reshape(-1)[0])
