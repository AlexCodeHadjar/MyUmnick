"""Порты: Protocol-интерфейсы, через которые ядро обращается к внешнему миру."""

from vtuber.ports.incoming import MessageSource
from vtuber.ports.llm import GenerationParams, LLMPort
from vtuber.ports.memory import EmbedderPort, MemoryStorePort
from vtuber.ports.resources import ManagedModel
from vtuber.ports.sink import ReplySink
from vtuber.ports.stt import STTPort, VadPort
from vtuber.ports.tts import TTSPort

__all__ = [
    "EmbedderPort",
    "GenerationParams",
    "LLMPort",
    "ManagedModel",
    "MemoryStorePort",
    "MessageSource",
    "ReplySink",
    "STTPort",
    "TTSPort",
    "VadPort",
]
