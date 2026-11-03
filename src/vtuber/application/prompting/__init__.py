"""Сборка промпта: персона, история, динамический блок — от неизменного к изменчивому (T-03)."""

from vtuber.application.prompting.context_budget import ContextBudget, ContextConfig
from vtuber.application.prompting.prompt_builder import (
    IMAGE_NOTE,
    Prompt,
    PromptBuilder,
    render_system_prompt,
)

__all__ = [
    "IMAGE_NOTE",
    "ContextBudget",
    "ContextConfig",
    "Prompt",
    "PromptBuilder",
    "render_system_prompt",
]
