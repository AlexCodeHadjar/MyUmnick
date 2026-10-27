"""Общее для скриптов бенчмарка и оценки: LLM-адаптер из конфига приложения и сбор ответа."""

from collections.abc import Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import Final

from vtuber.adapters.llm import LlamaCppLLM, OpenAICompatLLM
from vtuber.bootstrap import load_app_config
from vtuber.domain import Message
from vtuber.ports import GenerationParams, LLMPort

ROOT: Final = Path(__file__).resolve().parent.parent
BACKENDS: Final = MappingProxyType(
    {"llamacpp": LlamaCppLLM, "openai_compat": OpenAICompatLLM},
)
DEFAULT_BACKEND: Final = "llamacpp"
SYSTEM_PROMPT: Final = (
    "Ты Мика — дружелюбная и немного озорная виртуальная ведущая. Отвечай по-русски, живо "
    "и коротко: 1–3 предложения, если не просят подробнее. Если не знаешь ответа или не "
    "уверена — честно скажи об этом, не выдумывай. Не используй markdown, списки и эмодзи: "
    "ответ будет озвучен голосом."
)
"""Временный системный промпт до PromptBuilder (S-3.1); одинаков для бенчмарка и оценки."""


def open_llm(backend: str, env: Mapping[str, str]) -> OpenAICompatLLM:
    """Адаптер `backend` с секцией `[llm]` из config/*.toml и `env`; использовать в `async with`.

    Raises:
        ConfigError: конфиг не проходит проверку.

    """
    return BACKENDS[backend](load_app_config(ROOT, env).llm)


async def collect(llm: LLMPort, messages: Sequence[Message], params: GenerationParams) -> str:
    """Полный текст ответа."""
    return "".join([delta async for delta in llm.stream(messages, params)])
