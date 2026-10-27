"""Адаптеры языковых моделей (LLMPort)."""

from vtuber.adapters.llm.config import LLMConfig
from vtuber.adapters.llm.openai_compat import OpenAICompatLLM

__all__ = ["LLMConfig", "OpenAICompatLLM"]
