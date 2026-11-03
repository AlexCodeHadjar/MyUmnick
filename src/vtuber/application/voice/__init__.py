"""Голосовой ввод (Этап 11): нарезка речи на фразы, распознавание, перебивание."""

from vtuber.application.voice.addressing import (
    AddressedEvents,
    AddressingConfig,
    addressed,
)
from vtuber.application.voice.completeness import looks_unfinished
from vtuber.application.voice.listener import VoiceConfig, VoiceEvents, VoiceListener
from vtuber.application.voice.segmenter import (
    BargeIn,
    Segmenter,
    SegmenterConfig,
    SpeechEnded,
    SpeechStarted,
)

__all__ = [
    "AddressedEvents",
    "AddressingConfig",
    "BargeIn",
    "Segmenter",
    "SegmenterConfig",
    "SpeechEnded",
    "SpeechStarted",
    "VoiceConfig",
    "VoiceEvents",
    "VoiceListener",
    "addressed",
    "looks_unfinished",
]
