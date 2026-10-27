"""Числа словами для TTS: количественные, в именительном падеже.

Падеж «базовый»: с существительным после числа не согласуется, кроме собственных слов числа —
«тысяча», «миллион», «целая», «десятая».
"""

from typing import Final

type Forms = tuple[str, str, str]
"""Формы слова для 1, 2–4 и 5+: («тысяча», «тысячи», «тысяч»)."""

_UNITS: Final = ("", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять")
_UNITS_FEMININE: Final = ("", "одна", "две", *_UNITS[3:])
_TEENS: Final = (
    "десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать", "пятнадцать",
    "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать",
)  # fmt: skip
_TENS: Final = (
    "", "", "двадцать", "тридцать", "сорок", "пятьдесят", "шестьдесят", "семьдесят",
    "восемьдесят", "девяносто",
)  # fmt: skip
_HUNDREDS: Final = (
    "", "сто", "двести", "триста", "четыреста", "пятьсот", "шестьсот", "семьсот", "восемьсот",
    "девятьсот",
)  # fmt: skip
# Разряды от старшего: множитель, формы, женский ли род («одна тысяча», но «один миллион»).
_SCALES: Final[tuple[tuple[int, Forms, bool], ...]] = (
    (10**9, ("миллиард", "миллиарда", "миллиардов"), False),
    (10**6, ("миллион", "миллиона", "миллионов"), False),
    (10**3, ("тысяча", "тысячи", "тысяч"), True),
)
# Больше — уже не «число для разговора», а код или номер: читается по цифрам.
MAX_SPOKEN: Final = 10**12 - 1
_DIGITS: Final = ("ноль", *_UNITS[1:])
_FRACTIONS: Final[tuple[Forms, ...]] = (
    ("десятая", "десятых", "десятых"),
    ("сотая", "сотых", "сотых"),
    ("тысячная", "тысячных", "тысячных"),
)
_WHOLE: Final[Forms] = ("целая", "целых", "целых")
_TEEN_LOW, _TEEN_HIGH = 11, 19
_TEENS_START = 10
_FEW_LOW, _FEW_HIGH = 2, 4


def plural(number: int, forms: Forms) -> str:
    """Форма слова после числа: 1 тысяча, 3 тысячи, 5 тысяч, 11 тысяч, 21 тысяча."""
    last_two = abs(number) % 100
    last = last_two % 10
    if _TEEN_LOW <= last_two <= _TEEN_HIGH:
        return forms[2]
    if last == 1:
        return forms[0]
    return forms[1] if _FEW_LOW <= last <= _FEW_HIGH else forms[2]


def _triad(number: int, *, feminine: bool) -> list[str]:
    """0…999 словами; пусто для 0 (ноль — забота вызывающего)."""
    hundreds, rest = divmod(number, 100)
    words = [_HUNDREDS[hundreds]]
    if _TEENS_START <= rest < _TEENS_START + len(_TEENS):
        words.append(_TEENS[rest - _TEENS_START])
    else:
        tens, units = divmod(rest, 10)
        words += [_TENS[tens], (_UNITS_FEMININE if feminine else _UNITS)[units]]
    return [word for word in words if word]


def digits_to_words(digits: str) -> str:
    """По цифрам: «007» → «ноль ноль семь»."""
    return " ".join(_DIGITS[int(digit)] for digit in digits)


def integer_to_words(number: int, *, feminine: bool = False) -> str:
    """Целое словами; `feminine` — род единиц («одна целая», «две десятых»)."""
    if number < 0:
        return f"минус {integer_to_words(-number, feminine=feminine)}"
    if number == 0:
        return "ноль"
    if number > MAX_SPOKEN:
        return digits_to_words(str(number))
    words: list[str] = []
    for scale, forms, scale_feminine in _SCALES:
        count, number = divmod(number, scale)
        if count:
            words += [*_triad(count, feminine=scale_feminine), plural(count, forms)]
    words += _triad(number, feminine=feminine)
    return " ".join(words)


def decimal_to_words(whole: str, fraction: str) -> str:
    """Дробь из цифр до и после разделителя: «3», «5» → «три целых пять десятых».

    Больше трёх знаков после запятой — дробная часть по цифрам («три запятая один четыре…»).
    """
    whole_number = int(whole)
    if len(fraction) > len(_FRACTIONS):
        return f"{integer_to_words(whole_number)} запятая {digits_to_words(fraction)}"
    fraction_number = int(fraction)
    return " ".join(
        [
            integer_to_words(whole_number, feminine=True),
            plural(whole_number, _WHOLE),
            integer_to_words(fraction_number, feminine=True),
            plural(fraction_number, _FRACTIONS[len(fraction) - 1]),
        ]
    )
