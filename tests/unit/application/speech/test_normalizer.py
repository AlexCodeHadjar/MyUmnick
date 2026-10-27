import re

import pytest
from hypothesis import given
from hypothesis import strategies as st

from vtuber.application.speech import latin_word_to_russian, normalize_for_speech, spell

NBSP = chr(0xA0)
ZWJ = chr(0x200D)
SKIN_TONE = chr(0x1F3FB)


@pytest.mark.parametrize(
    ("text", "spoken"),
    [
        ("У меня 21 файл", "У меня двадцать один файл"),
        ("Число 3.5 и 2,25", "Число три целых пять десятых и две целых двадцать пять сотых"),
        ("Скорость -5, а 5-6 — диапазон", "Скорость минус пять, а пять-шесть — диапазон"),
        (f"Нас уже 1 000 000 и 1{NBSP}500", "Нас уже один миллион и одна тысяча пятьсот"),
        ("Агент 007", "Агент ноль ноль семь"),
        ("Скидка 50% и 1,5%", "Скидка пятьдесят процентов и одна целая пять десятых процента"),
        ("Всего 1% и 3 %", "Всего один процент и три процента"),
        ("Это 100км и GPT4", "Это сто км и джи пи ти четыре"),
        ("Версия 3.5.1", "Версия три целых пять десятых. один"),
    ],
)
def test_numbers_become_words(text: str, spoken: str) -> None:
    assert normalize_for_speech(text) == spoken


@pytest.mark.parametrize(
    ("text", "spoken"),
    [
        ("Яблоки, груши и т.д.", "Яблоки, груши и так далее"),
        ("Это, т. е. ничего", "Это, то есть ничего"),
        ("Т.к. поздно", "так как поздно"),
        ("См. выше, напр. тут", "смотри выше, например тут"),
        ("Цена 5 руб.", "Цена пять рублей"),
    ],
)
def test_abbreviations_are_expanded(text: str, spoken: str) -> None:
    assert normalize_for_speech(text) == spoken


def test_markup_emoji_and_symbols_are_spoken_or_dropped() -> None:
    text = f"**Привет** 👋{SKIN_TONE}, # заголовок `код` 2+2=4 & всё! 👨{ZWJ}💻"

    assert normalize_for_speech(text) == "Привет , заголовок код два плюс два равно четыре и всё!"


@pytest.mark.parametrize(
    ("word", "spoken"),
    [
        ("GPU", "джи пи ю"),
        ("I", "ай"),
        ("OK", "окей"),
        ("Python", "пайтон"),
        ("hello", "хелло"),
        ("Schiller", "шиллер"),
        ("chat", "чат"),
        ("NVIDIA", "нвидиа"),
    ],
)
def test_latin_words_read_in_russian(word: str, spoken: str) -> None:
    assert latin_word_to_russian(word) == spoken


def test_spell_names_letters() -> None:
    assert spell("Wx") == "дабл ю экс"


# Всё, что LLM может прислать в реплике: кириллица, латиница, цифры, знаки, эмодзи, разметка.
_ANYTHING = st.lists(
    st.sampled_from(
        [
            *list("абв АБВ abc XYZ 0123456789 .,-+=%&№@$€°*_#`~|<>[]{}^\\!?…—:;()\"'«»"),
            "👋",
            SKIN_TONE,
            ZWJ,
            NBSP,
            "т.е.",
            "млн",
            "\n",
        ]
    ),
    max_size=60,
).map("".join)


@given(_ANYTHING)
def test_output_has_no_digits_latin_markup_or_emoji(text: str) -> None:
    spoken = normalize_for_speech(text)

    assert not re.search(r"[0-9A-Za-z*_#`~|<>\[\]{}^\\%&@$€°+=№]", spoken)
    assert SKIN_TONE not in spoken
    assert "👋" not in spoken
    assert spoken == spoken.strip()
    assert "  " not in spoken
