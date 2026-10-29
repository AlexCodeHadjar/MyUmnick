"""Долговременная память (FR-10): факт о пользователе или мире и найденный по запросу факт."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import NewType

FactId = NewType("FactId", int)

type Vector = tuple[float, ...]
"""Эмбеддинг: единичной длины, поэтому близость — скалярное произведение (косинус)."""


class EmbedKind(StrEnum):
    """Что кодируется: у e5 запрос и запоминаемый текст кодируются по-разному."""

    QUERY = "query"
    PASSAGE = "passage"


class FactSource(StrEnum):
    """Откуда факт: от этого зависит доверие к нему при ответе."""

    USER = "user"
    """Пользователь сказал о себе прямо."""
    EXTRACTED = "extracted"
    """Извлечён из диалога LLM в простое (S-10.4)."""
    SUMMARY = "summary"
    """Резюме отрезанной истории (T-04)."""


@dataclass(frozen=True, slots=True)
class Fact:
    """Одна запоминаемая мысль; `importance` 0…1 — что вспоминать в первую очередь."""

    text: str
    source: FactSource
    importance: float
    created_at: datetime

    def __post_init__(self) -> None:
        if not 0 <= self.importance <= 1:
            msg = f"важность факта — от 0 до 1, получено {self.importance}"
            raise ValueError(msg)
        if self.created_at.tzinfo is None:
            msg = "время факта — с часовым поясом: без него сравнение дат между запусками ломается"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class FactHit:
    """Найденный факт; `score` — косинусная близость к запросу, −1…1, больше — ближе."""

    id: FactId
    fact: Fact
    score: float
