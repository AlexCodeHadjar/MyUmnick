import pytest

from vtuber.application.speech import (
    MAX_SPOKEN,
    decimal_to_words,
    digits_to_words,
    integer_to_words,
    plural,
)

THOUSANDS = ("тысяча", "тысячи", "тысяч")


@pytest.mark.parametrize(
    ("number", "form"),
    [(1, "тысяча"), (2, "тысячи"), (4, "тысячи"), (5, "тысяч"), (11, "тысяч"), (14, "тысяч"),
     (21, "тысяча"), (22, "тысячи"), (111, "тысяч"), (101, "тысяча"), (0, "тысяч")],
)  # fmt: skip
def test_plural_follows_russian_rules(number: int, form: str) -> None:
    assert plural(number, THOUSANDS) == form


@pytest.mark.parametrize(
    ("number", "words"),
    [
        (0, "ноль"),
        (7, "семь"),
        (12, "двенадцать"),
        (40, "сорок"),
        (101, "сто один"),
        (999, "девятьсот девяносто девять"),
        (1000, "одна тысяча"),
        (2000, "две тысячи"),
        (21_000, "двадцать одна тысяча"),
        (2024, "две тысячи двадцать четыре"),
        (1_000_000, "один миллион"),
        (2_500_000, "два миллиона пятьсот тысяч"),
        (3_000_000_001, "три миллиарда один"),
        (-15, "минус пятнадцать"),
    ],
)
def test_integer_to_words(number: int, words: str) -> None:
    assert integer_to_words(number) == words


def test_feminine_units_for_fractions() -> None:
    assert integer_to_words(1, feminine=True) == "одна"
    assert integer_to_words(22, feminine=True) == "двадцать две"


def test_too_large_number_is_read_by_digits() -> None:
    assert integer_to_words(MAX_SPOKEN + 1) == "один " + "ноль " * 11 + "ноль"
    assert digits_to_words("007") == "ноль ноль семь"


@pytest.mark.parametrize(
    ("whole", "fraction", "words"),
    [
        ("3", "5", "три целых пять десятых"),
        ("1", "25", "одна целая двадцать пять сотых"),
        ("0", "001", "ноль целых одна тысячная"),
        ("2", "2", "две целых две десятых"),
        ("3", "14159", "три запятая один четыре один пять девять"),
    ],
)
def test_decimal_to_words(whole: str, fraction: str, words: str) -> None:
    assert decimal_to_words(whole, fraction) == words
