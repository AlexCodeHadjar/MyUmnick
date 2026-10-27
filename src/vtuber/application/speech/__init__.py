"""Подготовка текста к синтезу речи: числа, сокращения, латиница, разметка (S-7.2)."""

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
    "MAX_SPOKEN",
    "Forms",
    "decimal_to_words",
    "digits_to_words",
    "integer_to_words",
    "latin_word_to_russian",
    "normalize_for_speech",
    "plural",
    "spell",
    "transliterate_latin",
]
