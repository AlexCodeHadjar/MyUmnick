"""Адаптеры голосового ввода: распознавание и детектор речи (ADR-0016)."""

from vtuber.adapters.stt.sensevoice import SenseVoiceConfig, SenseVoiceSounds
from vtuber.adapters.stt.silero_vad import SileroVad, VadConfig
from vtuber.adapters.stt.speaker_embedding import SherpaSpeakerEmbedder, SpeakerModelConfig
from vtuber.adapters.stt.whisper import WhisperConfig, WhisperSTT

__all__ = [
    "SenseVoiceConfig",
    "SenseVoiceSounds",
    "SherpaSpeakerEmbedder",
    "SileroVad",
    "SpeakerModelConfig",
    "VadConfig",
    "WhisperConfig",
    "WhisperSTT",
]
