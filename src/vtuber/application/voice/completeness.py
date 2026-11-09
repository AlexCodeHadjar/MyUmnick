"""Закончена ли фраза (S-14.2, ADR-0026): правила по тексту поверх паузы детектора.

Модель завершённости для русского не проверена, а явные случаи видны и так: «я хотел…» обрывается на
союзе, предлоге или начале мысли. Ошибка правила стоит недолгого ожидания, а не потери реплики.
"""

import re
from typing import Final

# Союзы, предлоги и начала мысли: законченная реплика на них не кончается.
_ENDINGS: Final = [
    "а",
    "и",
    "но",
    "или",
    "что",
    "чтобы",
    "если",
    "когда",
    "потому",
    "поэтому",
    "хотя",
    "в",
    "во",
    "на",
    "с",
    "со",
    "к",
    "ко",
    "у",
    "о",
    "об",
    "от",
    "до",
    "по",
    "за",
    "из",
    "под",
    "над",
    "при",
    "для",
    "без",
    "про",
    "через",
    "ну",
    "типа",
    "например",
    "значит",
    "короче",
    # Английское издание (Этап 20): союзы, предлоги, артикли — в русском таких слов нет.
    "and", "but", "or", "so", "because", "if", "when", "that", "the", "an", "to", "of", "in",
    "on", "with", "for", "my", "your", "like", "um", "uh",
]  # fmt: skip
_OPENINGS: Final = (
    "я хотел", "я хотела", "я думаю", "мне кажется", "то есть", "так как",
    "i wanted", "i think", "i mean", "it seems",
)  # fmt: skip
MIN_WORDS: Final = 2
_WORDS: Final = re.compile(r"[а-яёa-z']+", re.IGNORECASE)
_TRAILING_DOTS: Final = re.compile(r"(?:\.\.\.|…)\s*$")
_FINISHED_MARK: Final = re.compile(r"[?!]\s*$")


def looks_unfinished(text: str) -> bool:
    """Обрыв видно по многоточию или последним словам; вопрос и восклицание — конец точно."""
    if _FINISHED_MARK.search(text):
        return False
    if _TRAILING_DOTS.search(text):
        return True
    words = [word.lower() for word in _WORDS.findall(text)]
    # Короткий ответ («да», «ну») ждать незачем: скорость важнее (приоритет 1).
    if len(words) < MIN_WORDS:
        return False
    return words[-1] in _ENDINGS or " ".join(words[-2:]) in _OPENINGS
