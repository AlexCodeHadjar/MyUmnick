"""Адаптеры портов для контрактных тестов: каждый — в рабочем и в недоступном состоянии."""

from collections.abc import Callable
from dataclasses import dataclass

from tests.fakes import FakeLLM
from vtuber.ports import LLMPort

LONG_REPLY = (
    "Привет! Сегодня отличный день, чтобы поболтать о играх, аниме и всяких глупостях. " * 4
)


@dataclass(frozen=True, slots=True)
class LLMCase:
    """Как получить адаптер LLMPort: рабочий (долгий стрим) и с недоступным бэкендом."""

    name: str
    available: Callable[[], LLMPort]
    unavailable: Callable[[], LLMPort]


def llm_cases() -> list[LLMCase]:
    """Фейк — всегда; реальные адаптеры добавляются в своих сессиях (S-2.2, S-2.3)."""
    return [
        LLMCase(
            name="fake",
            available=lambda: FakeLLM(LONG_REPLY, chunk_size=3, delay_ms=2),
            unavailable=lambda: FakeLLM(LONG_REPLY, fail_after=0),
        ),
    ]
