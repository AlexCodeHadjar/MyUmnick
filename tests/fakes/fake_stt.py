"""Фейки голосового ввода: детектор по громкости и распознавание по сценарию (R-56)."""

import array
import asyncio
import math
import sys
from dataclasses import dataclass, field

from vtuber.domain import SAMPLE_WIDTH_BYTES, AudioChunk, AudioFormat, STTUnavailable

SAMPLE_RATE = 16_000
WINDOW = 512
LOUD = 0.02


@dataclass(slots=True)
class FakeVad:
    """Реализует VadPort: окно громче порога — речь. `resets` считает сбросы."""

    available: bool = True
    resets: int = 0

    @property
    def audio_format(self) -> AudioFormat:
        return AudioFormat(SAMPLE_RATE)

    @property
    def window_samples(self) -> int:
        return WINDOW

    async def speech_probability(self, pcm: bytes) -> float:
        if not self.available:
            raise STTUnavailable("FakeVad: модель не загружена (сценарий теста)")
        if len(pcm) != WINDOW * SAMPLE_WIDTH_BYTES:
            raise ValueError(f"окно VAD — {WINDOW} сэмплов, получено байт: {len(pcm)}")
        samples = array.array("h", pcm)
        if sys.byteorder == "big":
            samples.byteswap()
        rms = math.sqrt(sum(s * s for s in samples) / len(samples)) / 32768
        await asyncio.sleep(0)
        return 1.0 if rms > LOUD else 0.0

    def reset(self) -> None:
        self.resets += 1


@dataclass(slots=True)
class FakeSTT:
    """Реализует STTPort: `text` на любой непустой звук; вызовы — в `calls` (секунды, final)."""

    text: str = "привет"
    available: bool = True
    delay_s: float = 0
    calls: list[tuple[float, bool]] = field(default_factory=list)

    async def transcribe(self, audio: AudioChunk, *, final: bool) -> str:
        if not self.available:
            raise STTUnavailable("FakeSTT: модель не загружена (сценарий теста)")
        self.calls.append((audio.duration_s, final))
        await asyncio.sleep(self.delay_s)
        return self.text if audio.pcm else ""
