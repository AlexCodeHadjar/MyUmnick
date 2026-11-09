"""Сборка промпта: персона, история, динамический блок — от неизменного к изменчивому (T-03)."""

from vtuber.application.prompting.context_budget import ContextBudget, ContextConfig
from vtuber.application.prompting.prompt_builder import (
    IMAGE_NOTE,
    Prompt,
    PromptBuilder,
    render_system_prompt,
)
from vtuber.application.prompting.texts import EN_PROMPT, RU_PROMPT, PromptTexts

__all__ = [
    "EN_PROMPT",
    "IMAGE_NOTE",
    "RU_PROMPT",
    "ContextBudget",
    "ContextConfig",
    "Prompt",
    "PromptBuilder",
    "PromptTexts",
    "render_system_prompt",
]
