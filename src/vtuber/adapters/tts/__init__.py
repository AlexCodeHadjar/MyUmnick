"""Адаптеры синтеза речи (TTSPort)."""

from vtuber.adapters.tts.piper import (
    PiperConfig,
    PiperTTS,
    PiperVoiceLike,
    load_voice,
)
from vtuber.adapters.tts.silero import SileroConfig, SileroModel, SileroTTS, load_package, to_pcm

__all__ = [
    "PiperConfig",
    "PiperTTS",
    "PiperVoiceLike",
    "SileroConfig",
    "SileroModel",
    "SileroTTS",
    "load_package",
    "load_voice",
    "to_pcm",
]
