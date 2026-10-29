"""Нарезка потока текста на фразы для TTS: первая — раньше, чтобы звук начался быстрее (T-02).

Решение о разрезе принимается, только когда виден символ после знака: результат не зависит от
того, как поток побит на дельты (проверено property-тестом).
"""

from collections.abc import Iterator

from pydantic import Field

from vtuber.kernel import ConfigSection

HARD_STOPS = frozenset(".!?…")
SOFT_STOPS = frozenset(",;:—")
# Закрывающие кавычки и скобки остаются во фразе: «Привет!» режется после «»», а не после «!».
CLOSERS = frozenset("»\"')]’”")
# Точка после них — не конец фразы. В нижнем регистре, с точкой.
ABBREVIATIONS = frozenset(
    {
        "т.е.", "т.д.", "т.п.", "т.к.", "т.н.", "и.о.", "др.", "пр.", "см.", "ср.", "напр.",
        "г.", "гг.", "в.", "вв.", "ул.", "д.", "кв.", "стр.", "рис.", "табл.", "руб.", "коп.",
        "тыс.", "млн.", "млрд.", "мин.", "сек.", "ч.", "им.", "проф.", "доц.", "акад.", "англ.",
    }
)  # fmt: skip
# Инициал — заглавная буква с точкой: «А.».
INITIAL_LENGTH = 2


class ChunkerConfig(ConfigSection):
    """Секция `[pipeline.chunker]`.

    `first_min_words` — первая фраза режется по запятой не раньше стольких слов (1–2 слова
    звучат неестественно); `next_min_words` — то же для остальных; `max_words` — фраза без
    знаков режется по пробелу, чтобы TTS не ждал конца длинной тирады.
    """

    first_min_words: int = Field(gt=0)
    next_min_words: int = Field(gt=0)
    max_words: int = Field(gt=0)


def _token_before(text: str, end: int) -> str:
    """Слово, кончающееся на позиции `end` (включительно), в нижнем регистре."""
    start = end
    while start > 0 and not text[start - 1].isspace():
        start -= 1
    return text[start : end + 1].lower()


def _is_abbreviation(text: str, dot: int) -> bool:
    """Точка — часть сокращения («т.е.») или инициала («А. С. Пушкин»), а не конец фразы."""
    token = _token_before(text, dot)
    initial = len(token) == INITIAL_LENGTH and text[dot - 1].isupper()
    return token in ABBREVIATIONS or initial


class SentenceChunker:
    """Один экземпляр на ход: `feed(дельта)` отдаёт готовые фразы, `flush()` — хвост."""

    def __init__(self, cfg: ChunkerConfig) -> None:
        self._cfg = cfg
        self._buf = ""
        self._emitted = 0

    def feed(self, text: str) -> Iterator[str]:
        """Добавить текст; отдать фразы, конец которых уже точно известен."""
        self._buf += text
        while (cut := self._find_cut()) is not None:
            phrase, self._buf = self._buf[:cut].strip(), self._buf[cut:]
            if phrase:
                self._emitted += 1
                yield phrase

    def flush(self) -> str | None:
        """Конец ответа: остаток буфера — последняя фраза."""
        phrase, self._buf = self._buf.strip(), ""
        return phrase or None

    def _find_cut(self) -> int | None:
        """Первая позиция разреза или None — ждём следующую дельту."""
        min_words = self._cfg.first_min_words if self._emitted == 0 else self._cfg.next_min_words
        words = 0
        buf = self._buf
        for i, char in enumerate(buf[:-1]):
            if not char.isspace() and (i == 0 or buf[i - 1].isspace()):
                words += 1
            if (cut := self._cut_at(i, words, min_words)) is not None:
                return cut
        return None

    def _cut_at(self, i: int, words: int, min_words: int) -> int | None:
        """Разрез сразу после позиции `i`, если здесь кончается фраза; `buf[i + 1]` известен."""
        buf = self._buf
        char = buf[i]
        if char == "\n":
            return i + 1
        if char.isspace():
            return i if words >= self._cfg.max_words else None
        end = i
        while end + 1 < len(buf) and buf[end + 1] in CLOSERS:
            end += 1
        if end + 1 >= len(buf) or not buf[end + 1].isspace():
            return None
        hard = char in HARD_STOPS and not (char == "." and _is_abbreviation(buf, i))
        soft = char in SOFT_STOPS and words >= min_words
        return end + 1 if hard or soft else None
