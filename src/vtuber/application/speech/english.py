"""Фраза → текст для английского голоса (S-20.3): числа, годы, время, валюта, сокращения, кириллица.

Порядок как у русского нормализатора: сначала разметка и сокращения (в них точки), потом время,
валюта, проценты, порядковые, годы и числа, символы; кириллица — транслитом (голос её не читает).
"""

import re
import unicodedata
from typing import Final

from vtuber.application.speech.english_numbers import (
    english_decimal,
    english_digits,
    english_integer,
    english_ordinal,
    english_year,
)

_ABBREVIATIONS: Final = {
    "mr.": "mister", "mrs.": "missus", "ms.": "miz", "dr.": "doctor", "prof.": "professor",
    "st.": "saint", "jr.": "junior", "sr.": "senior", "vs.": "versus", "etc.": "et cetera",
    "e.g.": "for example", "i.e.": "that is", "approx.": "approximately", "no.": "number",
}  # fmt: skip
_ABBREVIATION = re.compile(
    "|".join(rf"(?<![\w.]){re.escape(key)}" for key in _ABBREVIATIONS), re.IGNORECASE
)
_UNITS: Final = {
    "km": "kilometers", "kg": "kilograms", "gb": "gigabytes", "mb": "megabytes", "tb": "terabytes",
    "ghz": "gigahertz", "mhz": "megahertz", "ms": "milliseconds", "fps": "frames per second",
    "cm": "centimeters", "mm": "millimeters", "kb": "kilobytes",
}  # fmt: skip
_NUM: Final = r"(?P<whole>\d{1,3}(?:,\d{3})+|\d+)(?:\.(?P<fraction>\d+))?"
_UNIT = re.compile(rf"(?<![\w.]){_NUM}\s?(?P<unit>{'|'.join(_UNITS)})\b", re.IGNORECASE)
_TIME = re.compile(
    r"\b(?P<h>\d{1,2}):(?P<m>\d{2})(?:\s?(?P<ampm>[ap]\.?m\.?)(?!\w))?", re.IGNORECASE
)
# «5 pm» без минут: время, а не «пять пм».
_HOUR_AMPM = re.compile(r"\b(?P<h>\d{1,2})\s?(?P<ampm>[ap])\.?m\.?(?!\w)", re.IGNORECASE)
_MONEY = re.compile(rf"(?P<cur>[$€£])\s?{_NUM}")
_CURRENCY: Final = {"$": ("dollar", "cents"), "€": ("euro", "cents"), "£": ("pound", "pence")}
_PERCENT = re.compile(rf"(?<![\w.]){_NUM}\s?%")
_ORDINAL = re.compile(r"\b(?P<n>\d+)(?:st|nd|rd|th)\b", re.IGNORECASE)
_YEAR = re.compile(r"(?<![\w.,$€£])(?P<year>1[1-9]\d\d|20\d\d)s?(?![\w.,]\d)")
_NUMBER = re.compile(rf"(?<![\w.,])(?P<sign>-)?{_NUM}(?![\w])")
_SYMBOLS: Final = {
    "+": " plus ", "=": " equals ", "&": " and ", "@": " at ", "%": " percent ", "#": " number ",
    "°": " degrees ", "№": " number ",
}  # fmt: skip
_SYMBOL = re.compile("|".join(re.escape(symbol) for symbol in _SYMBOLS))
_MARKUP = re.compile(r"[*_`~|<>\[\]{}^\\]")
_LETTER_DIGIT = re.compile(r"(?<=[^\W\d_])(?=\d)|(?<=\d)(?=[^\W\d_])")
_LEFTOVER_DIGITS = re.compile(r"\d+")
_CYRILLIC: Final = str.maketrans(
    {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "zh",
        "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o",
        "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts",
        "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu",
        "я": "ya",
    }
)  # fmt: skip
_INVISIBLE: Final = frozenset({"‍", "️", "︎"})
_DROPPED_CATEGORIES: Final = frozenset({"So", "Sk", "Cs"})
_NOON: Final = 12
_OH_MINUTES: Final = 10


def _amount(match: re.Match[str]) -> str:
    whole = match["whole"].replace(",", "")
    fraction = match["fraction"]
    return english_decimal(whole, fraction) if fraction else english_integer(int(whole))


def _number(match: re.Match[str]) -> str:
    whole = match["whole"].replace(",", "")
    if not match["fraction"] and len(whole) > 1 and whole.startswith("0"):
        return english_digits(whole)
    words = _amount(match)
    return f"minus {words}" if match["sign"] else words


def _money(match: re.Match[str]) -> str:
    unit, small = _CURRENCY[match["cur"]]
    whole = int(match["whole"].replace(",", ""))
    words = f"{english_integer(whole)} {unit}{'' if whole == 1 else 's'}"
    if unit == "pound" and whole != 1:
        words = f"{english_integer(whole)} pounds"
    fraction = match["fraction"]
    if fraction and int(fraction):
        words += f" {english_integer(int(fraction[:2].ljust(2, '0')))} {small}"
    return words


def _time(match: re.Match[str]) -> str:
    hours, minutes = int(match["h"]), int(match["m"])
    spoken = english_integer(hours)
    if minutes:
        oh = "oh " if minutes < _OH_MINUTES else ""
        spoken += f" {oh}{english_integer(minutes)}"
    elif not match["ampm"]:
        spoken += " o'clock" if hours <= _NOON else " hundred"
    if match["ampm"]:
        spoken += " a m" if match["ampm"].lower().startswith("a") else " p m"
        spoken += _kept_stop(match)
    return spoken


def _kept_stop(match: re.Match[str]) -> str:
    """«5 p.m.» в конце фразы: точка сокращения — заодно и конец фразы, его надо сохранить."""
    return "." if match.group().endswith(".") else ""


def _hour(match: re.Match[str]) -> str:
    return f"{english_integer(int(match['h']))} {match['ampm'].lower()} m{_kept_stop(match)}"


def _year(match: re.Match[str]) -> str:
    words = english_year(int(match["year"]))
    if match.group().endswith("s"):
        return f"{words[:-1]}ies" if words.endswith("y") else f"{words}s"
    return words


def _without_emoji(text: str) -> str:
    return "".join(
        char
        for char in text
        if char not in _INVISIBLE and unicodedata.category(char) not in _DROPPED_CATEGORIES
    )


def _cyrillic_to_latin(text: str) -> str:
    out: list[str] = []
    for char in text:
        lower = char.lower()
        latin = lower.translate(_CYRILLIC)
        out.append(latin.capitalize() if char != lower else latin)
    return "".join(out)


def normalize_english(text: str) -> str:
    """Фраза для английского TTS: только слова, пробелы и интонационные знаки."""
    text = _without_emoji(_MARKUP.sub(" ", text))
    text = _ABBREVIATION.sub(lambda m: _ABBREVIATIONS[m.group().lower()], text)
    text = _TIME.sub(_time, text)
    text = _HOUR_AMPM.sub(_hour, text)
    text = _MONEY.sub(_money, text)
    text = _PERCENT.sub(lambda m: f"{_amount(m)} percent", text)
    text = _UNIT.sub(lambda m: f"{_amount(m)} {_UNITS[m['unit'].lower()]}", text)
    text = _ORDINAL.sub(lambda m: english_ordinal(int(m["n"])), text)
    text = _YEAR.sub(_year, text)
    text = _LETTER_DIGIT.sub(" ", text)
    text = _NUMBER.sub(_number, text)
    text = _LEFTOVER_DIGITS.sub(lambda m: f" {english_digits(m.group())} ", text)
    text = _SYMBOL.sub(lambda m: _SYMBOLS[m.group()], text)
    return " ".join(_cyrillic_to_latin(text).split())
