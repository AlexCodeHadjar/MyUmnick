"""Подготовка текста к синтезу речи: числа, сокращения, латиница, разметка (S-7.2)."""

from vtuber.application.speech.diction import (
    EN_ABBREVIATIONS,
    EN_DICTION,
    RU_ABBREVIATIONS,
    RU_DICTION,
    Diction,
    Normalizer,
)
from vtuber.application.speech.english import normalize_english
from vtuber.application.speech.english_numbers import (
    english_integer,
    english_ordinal,
    english_year,
)
from vtuber.application.speech.latin import latin_word_to_russian, spell, transliterate_latin
from vtuber.application.speech.normalizer import normalize_for_speech
from vtuber.application.speech.numbers import (
    MAX_SPOKEN,
    Forms,
    decimal_to_words,
    digits_to_words,
    integer_to_words,
    plural,
)

__all__ = [
    "EN_ABBREVIATIONS",
    "EN_DICTION",
    "MAX_SPOKEN",
    "RU_ABBREVIATIONS",
    "RU_DICTION",
    "Diction",
    "Forms",
    "Normalizer",
    "decimal_to_words",
    "digits_to_words",
    "english_integer",
    "english_ordinal",
    "english_year",
    "integer_to_words",
    "latin_word_to_russian",
    "normalize_english",
    "normalize_for_speech",
    "plural",
    "spell",
    "transliterate_latin",
]
