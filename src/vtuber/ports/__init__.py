"""Порты: Protocol-интерфейсы, через которые ядро обращается к внешнему миру."""

from vtuber.ports.llm import GenerationParams, LLMPort

__all__ = ["GenerationParams", "LLMPort"]
