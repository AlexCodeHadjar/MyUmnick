"""Текст фразы → текст, который голос прочтёт правильно: без цифр, латиницы, разметки, эмодзи.

Порядок важен: сначала сокращения и разметка (в них точки и символы, которые иначе стали бы
словами), потом проценты (им нужно согласование), числа, символы и латиница.
"""

import re
import unicodedata
from typing import Final

from vtuber.application.speech.latin import transliterate_latin
from vtuber.application.speech.numbers import (
    Forms,
    decimal_to_words,
    digits_to_words,
    integer_to_words,
    plural,
)

# Сокращение → полная форма. Ключ — регулярка: точки буквальные, пробелы после них необязательны.
_ABBREVIATIONS: Final = {
    r"и\s?т\.\s?д\.": "и так далее",
    r"и\s?т\.\s?п\.": "и тому подобное",
    r"т\.\s?е\.": "то есть",
    r"т\.\s?к\.": "так как",
    r"т\.\s?н\.": "так называемый",
    r"напр\.": "например",
    r"см\.": "смотри",
    r"др\.": "другие",
    r"тыс\.": "тысяч",
    r"млн\.?": "миллионов",
    r"млрд\.?": "миллиардов",
    r"руб\.": "рублей",
}
_ABBREVIATION = re.compile(
    "|".join(rf"(?<!\w)(?:{pattern})" for pattern in _ABBREVIATIONS), re.IGNORECASE
)
_EXPANSIONS: Final = [
    (re.compile(rf"(?<!\w)(?:{pattern})", re.IGNORECASE), full)
    for pattern, full in _ABBREVIATIONS.items()
]

_PERCENT_FORMS: Final[Forms] = ("процент", "процента", "процентов")
# Число: знак минус только в начале слова («-5», но «5-6» — диапазон), группы тысяч через
# пробел («1 000 000»), дробная часть через точку или запятую без пробела («3.5», «3,5»).
_NUMBER = re.compile(
    r"(?<![\w.,])(?P<sign>-)?(?P<whole>\d{1,3}(?:[ \u00a0]\d{3})+|\d+)(?:[.,](?P<fraction>\d+))?"
    r"(?![\w])"
)
_PERCENT = re.compile(rf"{_NUMBER.pattern}\s?%")
_SYMBOLS: Final = {
    "+": " плюс ", "=": " равно ", "&": " и ", "№": " номер ", "@": " собака ", "%": " процентов ",
    "$": " долларов ", "€": " евро ", "°": " градусов ",
}  # fmt: skip
_SYMBOL = re.compile("|".join(re.escape(symbol) for symbol in _SYMBOLS))
# Разметка markdown и HTML-скобки: голос прочёл бы их как «звёздочка» или споткнулся бы.
_MARKUP = re.compile(r"[*_#`~|<>\[\]{}^\\]")
# Стык буквы и цифры («100км», «GPT4», «5G»): разделить, иначе число не отделится от слова.
_LETTER_DIGIT = re.compile(r"(?<=[^\W\d_])(?=\d)|(?<=\d)(?=[^\W\d_])")
# Что не стало числом (хвост версии «3.5.1», «1.2.3»), — по цифрам: цифр в речи быть не должно.
_LEFTOVER_DIGITS = re.compile(r"\d+")
_INVISIBLE: Final = frozenset({"\u200d", "\ufe0f", "\ufe0e"})
_DROPPED_CATEGORIES: Final = frozenset({"So", "Sk", "Cs"})


def _expand_abbreviation(match: re.Match[str]) -> str:
    text = match.group()
    for pattern, full in _EXPANSIONS:
        if pattern.fullmatch(text):
            return full
    return text


def _number_words(match: re.Match[str]) -> str:
    whole = re.sub(r"\D", "", match["whole"])
    fraction = match["fraction"]
    words = decimal_to_words(whole, fraction) if fraction else integer_to_words(int(whole))
    if not fraction and len(whole) > 1 and whole.startswith("0"):
        words = digits_to_words(whole)  # «007», «0123» — номер, а не количество
    return f"минус {words}" if match["sign"] else words


def _percent_words(match: re.Match[str]) -> str:
    # После дроби — «процента» («три целых пять десятых процента»), после целого — по числу.
    form = (
        _PERCENT_FORMS[1]
        if match["fraction"]
        else plural(int(re.sub(r"\D", "", match["whole"])), _PERCENT_FORMS)
    )
    return f"{_number_words(match)} {form}"


def _without_emoji(text: str) -> str:
    """Убрать пиктограммы (So), модификаторы вроде тона кожи (Sk), склейки и селекторы эмодзи."""
    return "".join(
        char
        for char in text
        if char not in _INVISIBLE and unicodedata.category(char) not in _DROPPED_CATEGORIES
    )


def normalize_for_speech(text: str) -> str:
    """Фраза для TTS: только слова, пробелы и знаки препинания, задающие интонацию."""
    text = _without_emoji(_MARKUP.sub(" ", text))
    text = _ABBREVIATION.sub(_expand_abbreviation, text)
    text = _LETTER_DIGIT.sub(" ", text)
    text = _PERCENT.sub(_percent_words, text)
    text = _NUMBER.sub(_number_words, text)
    text = _LEFTOVER_DIGITS.sub(lambda match: f" {digits_to_words(match.group())} ", text)
    text = _SYMBOL.sub(lambda match: _SYMBOLS[match.group()], text)
    text = transliterate_latin(text)
    return " ".join(text.split())
