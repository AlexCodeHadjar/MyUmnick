"""Латиница для русского TTS: русские голоса латиницу не читают или читают по-своему.

Аббревиатуры (GPU) — по названиям букв, известные слова — из словаря, прочее — приблизительный
транслит по буквосочетаниям. Произношение «как в английском» не цель: цель — чтобы голос не
спотыкался и слово было узнаваемо.
"""

import re
from typing import Final

_LETTER_NAMES: Final = {
    "a": "эй", "b": "би", "c": "си", "d": "ди", "e": "и", "f": "эф", "g": "джи", "h": "эйч",
    "i": "ай", "j": "джей", "k": "кей", "l": "эл", "m": "эм", "n": "эн", "o": "оу", "p": "пи",
    "q": "кью", "r": "ар", "s": "эс", "t": "ти", "u": "ю", "v": "ви", "w": "дабл ю", "x": "экс",
    "y": "уай", "z": "зед",
}  # fmt: skip
# Частые в речи витюбера слова, транслит которых звучал бы странно. Расширяется по мере надобности.
_KNOWN_WORDS: Final = {
    "ok": "окей", "okay": "окей", "python": "пайтон", "youtube": "ютуб", "google": "гугл",
    "windows": "виндоус", "twitch": "твич", "discord": "дискорд", "steam": "стим",
    "minecraft": "майнкрафт", "iphone": "айфон", "wifi": "вайфай", "vtuber": "витюбер",
    "anime": "аниме", "game": "гейм", "online": "онлайн", "live": "лайв", "stream": "стрим",
}  # fmt: skip
# Сначала длинные сочетания: «sch» раньше «sh» и «s».
_COMBINATIONS: Final = (
    ("sch", "ш"), ("sh", "ш"), ("ch", "ч"), ("zh", "ж"), ("th", "т"), ("ph", "ф"), ("kh", "х"),
    ("ts", "ц"), ("ck", "к"), ("qu", "кв"), ("oo", "у"), ("ee", "и"), ("ea", "и"), ("ya", "я"),
    ("yu", "ю"), ("yo", "ё"),
)  # fmt: skip
_LETTERS: Final = {
    "a": "а", "b": "б", "c": "к", "d": "д", "e": "е", "f": "ф", "g": "г", "h": "х", "i": "и",
    "j": "дж", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о", "p": "п", "q": "к", "r": "р",
    "s": "с", "t": "т", "u": "у", "v": "в", "w": "в", "x": "кс", "y": "и", "z": "з",
}  # fmt: skip
_ACRONYM_MAX = 5
_WORD = re.compile(r"[A-Za-z]+")


def spell(word: str) -> str:
    """По названиям букв: «GPU» → «джи пи ю»."""
    return " ".join(_LETTER_NAMES[letter] for letter in word.lower())


def _transliterate(word: str) -> str:
    lower, out, i = word.lower(), [], 0
    while i < len(lower):
        for latin, cyrillic in _COMBINATIONS:
            if lower.startswith(latin, i):
                out.append(cyrillic)
                i += len(latin)
                break
        else:
            out.append(_LETTERS[lower[i]])
            i += 1
    return "".join(out)


def latin_word_to_russian(word: str) -> str:
    """Одно латинское слово по-русски: словарь, аббревиатура по буквам или транслит."""
    if (known := _KNOWN_WORDS.get(word.lower())) is not None:
        return known
    if word.isupper() and len(word) <= _ACRONYM_MAX:
        return spell(word)
    return _transliterate(word)


def transliterate_latin(text: str) -> str:
    """Все латинские слова текста — по-русски; остальное без изменений."""
    return _WORD.sub(lambda match: latin_word_to_russian(match.group()), text)
