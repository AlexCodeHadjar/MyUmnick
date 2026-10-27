"""Эмоции витюбера и формат их тегов в ответе LLM: `<happy>Привет!`."""

from enum import StrEnum
from typing import Final

TAG_OPEN: Final = "<"
TAG_CLOSE: Final = ">"


class Emotion(StrEnum):
    """Единственный источник списка эмоций: из него строятся промпт персоны и разбор ответа."""

    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SURPRISED = "surprised"
    EMBARRASSED = "embarrassed"
    THINKING = "thinking"

    @property
    def tag(self) -> str:
        """Тег эмоции в тексте ответа, например `<happy>`."""
        return f"{TAG_OPEN}{self.value}{TAG_CLOSE}"


MAX_TAG_LENGTH: Final = max(len(emotion.tag) for emotion in Emotion)
"""Длина самого длинного тега: дальше этого разборщику потока нет смысла ждать `>`."""


def parse_tag(tag: str) -> Emotion | None:
    """Возвращает эмоцию по тегу вида `<happy>` или None, если тег неизвестен или искажён.

    Регистр и пробелы внутри скобок не важны: модели иногда пишут `<Happy>`.
    """
    if not (tag.startswith(TAG_OPEN) and tag.endswith(TAG_CLOSE)):
        return None
    name = tag[len(TAG_OPEN) : len(tag) - len(TAG_CLOSE)].strip().lower()
    try:
        return Emotion(name)
    except ValueError:
        return None
