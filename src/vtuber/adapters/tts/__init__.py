"""Адаптеры синтеза речи (TTSPort)."""

from vtuber.adapters.tts.silero import SileroConfig, SileroModel, SileroTTS, load_package, to_pcm

__all__ = ["SileroConfig", "SileroModel", "SileroTTS", "load_package", "to_pcm"]
