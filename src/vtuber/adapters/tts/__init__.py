"""Адаптеры синтеза речи (TTSPort)."""

from vtuber.adapters.tts.config import TTSConfig
from vtuber.adapters.tts.fallback import FallbackTTS
from vtuber.adapters.tts.piper import (
    PiperConfig,
    PiperTTS,
    PiperVoiceLike,
    load_voice,
)
from vtuber.adapters.tts.silero import SileroConfig, SileroModel, SileroTTS, load_package, to_pcm
from vtuber.adapters.tts.voice_server import VoiceServerConfig, VoiceServerTTS

__all__ = [
    "FallbackTTS",
    "PiperConfig",
    "PiperTTS",
    "PiperVoiceLike",
    "SileroConfig",
    "SileroModel",
    "SileroTTS",
    "TTSConfig",
    "VoiceServerConfig",
    "VoiceServerTTS",
    "load_package",
    "load_voice",
    "to_pcm",
]
