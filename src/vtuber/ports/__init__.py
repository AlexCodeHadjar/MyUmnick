"""Порты: Protocol-интерфейсы, через которые ядро обращается к внешнему миру."""

from vtuber.ports.llm import GenerationParams, LLMPort
from vtuber.ports.memory import EmbedderPort, MemoryStorePort
from vtuber.ports.sink import ReplySink
from vtuber.ports.stt import STTPort, VadPort
from vtuber.ports.tts import TTSPort

__all__ = [
    "EmbedderPort",
    "GenerationParams",
    "LLMPort",
    "MemoryStorePort",
    "ReplySink",
    "STTPort",
    "TTSPort",
    "VadPort",
]
