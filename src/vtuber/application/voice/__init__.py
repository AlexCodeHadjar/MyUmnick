"""Голосовой ввод (Этап 11): нарезка речи на фразы, распознавание, перебивание."""

from vtuber.application.voice.addressing import (
    AddressedEvents,
    AddressingConfig,
    addressed,
    name_pattern,
    without_call,
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
from vtuber.application.voice.sounds import (
    REACTIONS,
    SoundActions,
    SoundsConfig,
    SoundWatcher,
    loudness,
)
from vtuber.application.voice.speakers import (
    SpeakerLabeler,
    SpeakersConfig,
    SpeakerTracker,
    labelled,
)

__all__ = [
    "REACTIONS",
    "AddressedEvents",
    "AddressingConfig",
    "BargeIn",
    "Segmenter",
    "SegmenterConfig",
    "SoundActions",
    "SoundWatcher",
    "SoundsConfig",
    "SpeakerLabeler",
    "SpeakerTracker",
    "SpeakersConfig",
    "SpeechEnded",
    "SpeechStarted",
    "VoiceConfig",
    "VoiceEvents",
    "VoiceListener",
    "addressed",
    "labelled",
    "looks_unfinished",
    "loudness",
    "name_pattern",
    "without_call",
]
