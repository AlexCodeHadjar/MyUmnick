"""Звук речи: формат PCM и фрагменты синтезированного аудио."""

from dataclasses import dataclass
from typing import Final

SAMPLE_WIDTH_BYTES: Final = 2
"""PCM s16le: два байта на сэмпл."""


@dataclass(frozen=True, slots=True)
class AudioFormat:
    """Формат звука: PCM s16le, моно — так звук передаётся в UI (ADR-0003)."""

    sample_rate: int

    @property
    def bytes_per_second(self) -> int:
        """Объём одной секунды звука в байтах."""
        return self.sample_rate * SAMPLE_WIDTH_BYTES


@dataclass(frozen=True, slots=True)
class AudioChunk:
    """Непрерывный фрагмент PCM в формате `format`."""

    format: AudioFormat
    pcm: bytes

    @property
    def duration_s(self) -> float:
        """Длительность фрагмента в секундах (для RTF и пауз между фразами)."""
        return len(self.pcm) / self.format.bytes_per_second
