"""Доменный слой: неизменяемые сущности и значения диалога, речи и эмоций."""

from vtuber.domain.dialogue import Message, Persona, Role, Turn, TurnId
from vtuber.domain.emotion import MAX_TAG_LENGTH, TAG_CLOSE, TAG_OPEN, Emotion, parse_tag
from vtuber.domain.errors import (
    BackendUnavailable,
    ConfigError,
    GenerationFailed,
    LLMUnavailable,
    ProtocolError,
    TTSUnavailable,
    VtuberError,
)
from vtuber.domain.events import (
    BackendState,
    BackendStatusChanged,
    CancelReason,
    Component,
    EmotionChanged,
    TurnCancelled,
    TurnFinished,
    TurnStarted,
)
from vtuber.domain.speech import SAMPLE_WIDTH_BYTES, AudioChunk, AudioFormat

__all__ = [
    "MAX_TAG_LENGTH",
    "SAMPLE_WIDTH_BYTES",
    "TAG_CLOSE",
    "TAG_OPEN",
    "AudioChunk",
    "AudioFormat",
    "BackendState",
    "BackendStatusChanged",
    "BackendUnavailable",
    "CancelReason",
    "Component",
    "ConfigError",
    "Emotion",
    "EmotionChanged",
    "GenerationFailed",
    "LLMUnavailable",
    "Message",
    "Persona",
    "ProtocolError",
    "Role",
    "TTSUnavailable",
    "Turn",
    "TurnCancelled",
    "TurnFinished",
    "TurnId",
    "TurnStarted",
    "VtuberError",
    "parse_tag",
]
