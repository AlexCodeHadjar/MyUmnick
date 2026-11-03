"""Сборка промпта хода от неизменного к изменчивому — чтобы KV-кэш префикса жил между ходами."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from vtuber.domain import AttachedImage, Emotion, Gesture, Message, Persona, Role

EMOTIONS_PLACEHOLDER: Final = "{emotions}"
GESTURES_PLACEHOLDER: Final = "{gestures}"
IMAGE_NOTE: Final = "(показана картинка, сейчас её уже не видно)"
# Справка после реплики: начало реплики остаётся общим с прогревом черновика (T-05) и историей.
CONTEXT_TEMPLATE: Final = "{user_text}\n(Справка для тебя, пользователь её не видит: {context})"


@dataclass(frozen=True, slots=True)
class Prompt:
    """Сообщения для LLM; первые `prefix_length` — неизменный префикс (персона и примеры)."""

    messages: tuple[Message, ...]
    prefix_length: int


class PromptBuilder:
    """Строит промпт: [персона + примеры] → [история] → [справка + реплика] (T-03).

    Префикс собирается один раз в конструкторе и потом не меняется — поэтому он байт-в-байт
    одинаков на всех ходах, и llama-server пересчитывает только хвост. Динамика (время,
    найденные факты) — только в последней реплике, никогда не в системном промпте.
    """

    def __init__(self, persona: Persona) -> None:
        self._prefix = (Message(Role.SYSTEM, render_system_prompt(persona)), *persona.examples)

    @property
    def prefix(self) -> tuple[Message, ...]:
        """Неизменная часть промпта — её прогревают в KV-кэше при старте (T-06)."""
        return self._prefix

    def build(
        self,
        history: Sequence[Message],
        user_text: str,
        context: Sequence[str] = (),
        images: tuple[AttachedImage, ...] = (),
    ) -> Prompt:
        """Промпт хода. `history` только дописывается между ходами (её ведёт память, T-04)."""
        user = Message(Role.USER, _with_context(user_text, context), images)
        return Prompt((*self._prefix, *history, user), len(self._prefix))


def render_system_prompt(persona: Persona) -> str:
    """Системный промпт персоны; `{emotions}` в правилах → теги всех эмоций из `Emotion`."""
    tags = ", ".join(emotion.tag for emotion in Emotion)
    gestures = ", ".join(gesture.tag for gesture in Gesture)
    rules = [
        f"- {rule.replace(EMOTIONS_PLACEHOLDER, tags).replace(GESTURES_PLACEHOLDER, gestures)}"
        for rule in persona.rules
    ]
    parts = [
        f"Ты — {persona.name}.",
        persona.description,
        f"Манера речи: {persona.speech_style}" if persona.speech_style else "",
        f"Язык общения: {persona.language}.",
        "Правила:" if rules else "",
        *rules,
    ]
    return "\n".join(part for part in parts if part)


def _with_context(user_text: str, context: Sequence[str]) -> str:
    if not context:
        return user_text
    return CONTEXT_TEMPLATE.format(context=" ".join(context), user_text=user_text)
