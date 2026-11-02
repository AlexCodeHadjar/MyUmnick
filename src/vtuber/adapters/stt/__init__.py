"""Адаптеры голосового ввода: распознавание и детектор речи (ADR-0016)."""

from vtuber.adapters.stt.silero_vad import SileroVad, VadConfig
from vtuber.adapters.stt.whisper import WhisperConfig, WhisperSTT

__all__ = ["SileroVad", "VadConfig", "WhisperConfig", "WhisperSTT"]
