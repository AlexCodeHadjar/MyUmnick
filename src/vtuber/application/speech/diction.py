"""Дикция издания (Этап 20, ADR-0032): нормализатор фраз и сокращения для нарезки.

Выбирается один раз при сборке голоса: в горячем пути нет проверок языка (приоритет 1).
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from vtuber.application.speech.english import normalize_english
from vtuber.application.speech.normalizer import normalize_for_speech

type Normalizer = Callable[[str], str]
"""Фраза → текст, который голос прочтёт правильно."""

# Точка после них — не конец фразы. В нижнем регистре, с точкой.
RU_ABBREVIATIONS: Final = frozenset(
    {
        "т.е.", "т.д.", "т.п.", "т.к.", "т.н.", "и.о.", "др.", "пр.", "см.", "ср.", "напр.",
        "г.", "гг.", "в.", "вв.", "ул.", "д.", "кв.", "стр.", "рис.", "табл.", "руб.", "коп.",
        "тыс.", "млн.", "млрд.", "мин.", "сек.", "ч.", "им.", "проф.", "доц.", "акад.", "англ.",
    }
)  # fmt: skip
EN_ABBREVIATIONS: Final = frozenset(
    {
        "mr.", "mrs.", "ms.", "dr.", "prof.", "st.", "jr.", "sr.", "vs.", "etc.", "e.g.", "i.e.",
        "u.s.", "u.k.", "a.m.", "p.m.", "approx.", "no.", "inc.", "ltd.", "co.", "dept.", "min.",
        "sec.", "fig.", "vol.", "ch.", "ave.", "blvd.", "jan.", "feb.", "mar.", "apr.", "jun.",
        "jul.", "aug.", "sep.", "sept.", "oct.", "nov.", "dec.",
    }
)  # fmt: skip


@dataclass(frozen=True, slots=True)
class Diction:
    """Нормализатор фраз для голоса и сокращения, на точке которых фраза не режется."""

    normalize: Normalizer
    abbreviations: frozenset[str]


RU_DICTION: Final = Diction(normalize_for_speech, RU_ABBREVIATIONS)
EN_DICTION: Final = Diction(normalize_english, EN_ABBREVIATIONS)
