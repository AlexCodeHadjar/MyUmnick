"""Порты: Protocol-интерфейсы, через которые ядро обращается к внешнему миру."""

from vtuber.ports.llm import GenerationParams, LLMPort
from vtuber.ports.sink import ReplySink

__all__ = ["GenerationParams", "LLMPort", "ReplySink"]
