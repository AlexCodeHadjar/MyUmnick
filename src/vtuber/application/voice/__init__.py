"""Голосовой ввод (Этап 11): нарезка речи на фразы, распознавание, перебивание."""

from vtuber.application.voice.listener import VoiceConfig, VoiceEvents, VoiceListener
from vtuber.application.voice.segmenter import (
    BargeIn,
    Segmenter,
    SegmenterConfig,
    SpeechEnded,
    SpeechStarted,
)

__all__ = [
    "BargeIn",
    "Segmenter",
    "SegmenterConfig",
    "SpeechEnded",
    "SpeechStarted",
    "VoiceConfig",
    "VoiceEvents",
    "VoiceListener",
]
