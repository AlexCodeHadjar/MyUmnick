"""Числа словами по-английски (S-20.3): количественные, порядковые, годы, дроби — без зависимостей.

`num2words` под LGPL — ради чисел тянуть его не стоит (STAGE_20, 4.6).
"""

from typing import Final

from vtuber.application.speech.numbers import MAX_SPOKEN

_UNITS: Final = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
    "nineteen",
)  # fmt: skip
_TENS: Final = (
    "", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
)  # fmt: skip
_SCALES: Final = ((10**9, "billion"), (10**6, "million"), (10**3, "thousand"))
_ORDINAL_WORDS: Final = {
    "one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth",
    "nine": "ninth", "twelve": "twelfth",
}  # fmt: skip
_HUNDRED: Final = 100
_TEEN_LIMIT: Final = 20
_YEAR_MIN: Final = 1100
_YEAR_MAX: Final = 2099
_CENTURY_ROUND: Final = 2000
_OH_LIMIT: Final = 10


def english_integer(number: int) -> str:
    """«1234» → «one thousand two hundred thirty-four»; больше `MAX_SPOKEN` — по цифрам."""
    if number < 0:
        return f"minus {english_integer(-number)}"
    if number > MAX_SPOKEN:
        return english_digits(str(number))
    if number < _HUNDRED:
        return _below_hundred(number)
    return _with_scale(number)


def _with_scale(number: int) -> str:
    for scale, name in _SCALES:
        if number >= scale:
            head, rest = divmod(number, scale)
            tail = f" {english_integer(rest)}" if rest else ""
            return f"{english_integer(head)} {name}{tail}"
    head, rest = divmod(number, _HUNDRED)
    tail = f" {_below_hundred(rest)}" if rest else ""
    return f"{_UNITS[head]} hundred{tail}"


def english_digits(digits: str) -> str:
    """«007» → «zero zero seven»: номер, а не количество."""
    return " ".join(_UNITS[int(digit)] for digit in digits if digit.isdigit())


def english_decimal(whole: str, fraction: str) -> str:
    """«3», «14» → «three point one four»."""
    return f"{english_integer(int(whole))} point {english_digits(fraction)}"


def english_ordinal(number: int) -> str:
    """«21» → «twenty-first»."""
    words = english_integer(number)
    head, sep, last = words.rpartition("-") if "-" in words.split()[-1] else words.rpartition(" ")
    if last in _ORDINAL_WORDS:
        last = _ORDINAL_WORDS[last]
    elif last.endswith("y"):
        last = f"{last[:-1]}ieth"
    else:
        last = f"{last}th"
    return f"{head}{sep}{last}"


def english_year(number: int) -> str:
    """«1999» → «nineteen ninety-nine», «2024» → «twenty twenty-four», «2005» → «two thousand five».

    Вне 1100–2099 — как обычное число.
    """
    if not _YEAR_MIN <= number <= _YEAR_MAX:
        return english_integer(number)
    if _CENTURY_ROUND <= number < _CENTURY_ROUND + _OH_LIMIT:
        return english_integer(number)
    head, tail = divmod(number, _HUNDRED)
    if tail == 0:
        return f"{english_integer(head)} hundred"
    rest = f"oh {_UNITS[tail]}" if tail < _OH_LIMIT else _below_hundred(tail)
    return f"{english_integer(head)} {rest}"


def _below_hundred(number: int) -> str:
    if number < _TEEN_LIMIT:
        return _UNITS[number]
    tens, units = divmod(number, _OH_LIMIT)
    return _TENS[tens] if units == 0 else f"{_TENS[tens]}-{_UNITS[units]}"
