"""Языковой пакет издания (Этап 20, ADR-0032): тексты и правила ядра, зависящие от языка.

Тексты лежат рядом со своими модулями («один факт — одно место»), пакет их только собирает.
Выбирается один раз при сборке объектов: в горячем пути проверок языка нет (приоритет 1).
"""

from dataclasses import dataclass
from typing import Final

from vtuber.application.memory import EN_MEMORY, RU_MEMORY, MemoryTexts
from vtuber.application.prompting import EN_PROMPT, RU_PROMPT, PromptTexts
from vtuber.application.speech import EN_DICTION, RU_DICTION, Diction


@dataclass(frozen=True, slots=True)
class LanguagePack:
    """Рамка промпта и служебные реплики, память, дикция голоса."""

    language: str
    prompt: PromptTexts
    memory: MemoryTexts
    diction: Diction


RU_PACK: Final = LanguagePack("ru", RU_PROMPT, RU_MEMORY, RU_DICTION)
EN_PACK: Final = LanguagePack("en", EN_PROMPT, EN_MEMORY, EN_DICTION)
