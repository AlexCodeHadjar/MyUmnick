"""Сборка промпта: персона, история, динамический блок — от неизменного к изменчивому (T-03)."""

from vtuber.application.prompting.context_budget import ContextBudget, ContextConfig
from vtuber.application.prompting.profile import FloorGuard, with_profile
from vtuber.application.prompting.prompt_builder import (
    IMAGE_NOTE,
    Prompt,
    PromptBuilder,
    render_system_prompt,
)
from vtuber.application.prompting.texts import (
    EN_PROFILE,
    EN_PROMPT,
    RU_PROFILE,
    RU_PROMPT,
    ProfileTexts,
    PromptTexts,
)

__all__ = [
    "EN_PROFILE",
    "EN_PROMPT",
    "IMAGE_NOTE",
    "RU_PROFILE",
    "RU_PROMPT",
    "ContextBudget",
    "ContextConfig",
    "FloorGuard",
    "ProfileTexts",
    "Prompt",
    "PromptBuilder",
    "PromptTexts",
    "render_system_prompt",
    "with_profile",
]
