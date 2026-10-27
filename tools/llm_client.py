"""Общее для скриптов бенчмарка и оценки: LLM-адаптер из конфига приложения и сбор ответа."""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final

from vtuber.adapters.llm import OpenAICompatLLM
from vtuber.bootstrap import llm_backends, load_app_config
from vtuber.domain import Message
from vtuber.ports import GenerationParams, LLMPort

ROOT: Final = Path(__file__).resolve().parent.parent
SYSTEM_PROMPT: Final = (
    "Ты Мика — дружелюбная и немного озорная виртуальная ведущая. Отвечай по-русски, живо "
    "и коротко: 1–3 предложения, если не просят подробнее. Если не знаешь ответа или не "
    "уверена — честно скажи об этом, не выдумывай. Не используй markdown, списки и эмодзи: "
    "ответ будет озвучен голосом."
)
"""Временный системный промпт до PromptBuilder (S-3.1); одинаков для бенчмарка и оценки."""


def open_llm(backend: str | None, env: Mapping[str, str]) -> OpenAICompatLLM:
    """Адаптер из реестра приложения по `backend` (по умолчанию — `[llm].backend` конфига).

    Использовать в `async with`.

    Raises:
        ConfigError: конфиг не проходит проверку или бэкенд неизвестен.

    """
    cfg = load_app_config(ROOT, env).llm
    return llm_backends().create(backend or cfg.backend, cfg)


async def collect(llm: LLMPort, messages: Sequence[Message], params: GenerationParams) -> str:
    """Полный текст ответа."""
    return "".join([delta async for delta in llm.stream(messages, params)])
