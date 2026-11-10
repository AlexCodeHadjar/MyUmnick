"""Порты: Protocol-интерфейсы, через которые ядро обращается к внешнему миру."""

from vtuber.ports.chats import ChatCatalogPort
from vtuber.ports.incoming import MessageSource
from vtuber.ports.llm import GenerationParams, LLMPort
from vtuber.ports.memory import EmbedderPort, MemoryStorePort, MemoryVaultPort
from vtuber.ports.resources import GpuProbe, ManagedModel
from vtuber.ports.setup import FileFetcher
from vtuber.ports.sink import ReplySink
from vtuber.ports.stt import SoundClassifierPort, SpeakerEmbedderPort, STTPort, VadPort
from vtuber.ports.tts import TTSPort

__all__ = [
    "ChatCatalogPort",
    "EmbedderPort",
    "FileFetcher",
    "GenerationParams",
    "GpuProbe",
    "LLMPort",
    "ManagedModel",
    "MemoryStorePort",
    "MemoryVaultPort",
    "MessageSource",
    "ReplySink",
    "STTPort",
    "SoundClassifierPort",
    "SpeakerEmbedderPort",
    "TTSPort",
    "VadPort",
]
