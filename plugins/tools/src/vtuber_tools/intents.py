"""Что просит реплика: разбор без модели, микросекунды вместо лишнего раунда LLM."""

import re
from dataclasses import dataclass
from typing import Final

_SECONDS_IN: Final = {"сек": 1, "мин": 60, "час": 3600}
_NUMBERS: Final = {
    "одну": 1,
    "один": 1,
    "две": 2,
    "два": 2,
    "три": 3,
    "четыре": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
    "пятнадцать": 15,
    "двадцать": 20,
    "тридцать": 30,
    "сорок": 40,
    "пятьдесят": 50,
}
_NUMBER_WORDS: Final = "|".join(_NUMBERS)

_TIME: Final = re.compile(
    r"\b(который час|сколько (сейчас )?времени|какое (сегодня |сейчас )?число"
    r"|какой (сегодня |сейчас )?день|какая (сегодня |сейчас )?дата)\b",
    re.IGNORECASE,
)
_TIMER: Final = re.compile(
    rf"\b(таймер\w*|напомни\w*)\b.*?\b(на|через)\s+"
    rf"(?:(?P<count>\d+|{_NUMBER_WORDS})\s+)?(?P<unit>сек|мин|час)\w*"
    r"(?P<about>\s+.+)?$",
    re.IGNORECASE,
)
_HALF_HOUR: Final = re.compile(r"\b(таймер\w*|напомни\w*)\b.*?\bполчаса\b", re.IGNORECASE)
_NOTE_ADD: Final = re.compile(
    r"\b(запиши|добавь|сохрани)\b(?:\s+\S+){0,2}?\s+(?:заметк\w*|в заметки)"
    r"\s*[:,-]?\s*(?P<text>.+)$",
    re.IGNORECASE,
)
_NOTES_LIST: Final = re.compile(
    r"\b(покажи|прочитай|прочти|какие|зачитай|что в)\b.*\bзаметк\w*", re.IGNORECASE
)


@dataclass(frozen=True, slots=True)
class AskTime:
    """Вопрос о времени или дате."""


@dataclass(frozen=True, slots=True)
class SetTimer:
    """Поставить таймер; `about` — о чём напомнить."""

    seconds: int
    about: str


@dataclass(frozen=True, slots=True)
class AddNote:
    """Записать заметку."""

    text: str


@dataclass(frozen=True, slots=True)
class ListNotes:
    """Прочитать заметки."""


type Intent = AskTime | SetTimer | AddNote | ListNotes


def detect_intent(text: str) -> Intent | None:
    """Намерение реплики; None — обычная реплика, инструменты ни при чём."""
    return _note_intent(text) or _timer_intent(text) or _time_intent(text)


def _note_intent(text: str) -> AddNote | ListNotes | None:
    if (note := _NOTE_ADD.search(text)) is not None:
        return AddNote(note["text"].strip())
    return ListNotes() if _NOTES_LIST.search(text) is not None else None


def _timer_intent(text: str) -> SetTimer | None:
    if _HALF_HOUR.search(text) is not None:
        return SetTimer(1800, "")
    timer = _TIMER.search(text)
    return None if timer is None else _timer(timer)


def _time_intent(text: str) -> AskTime | None:
    return AskTime() if _TIME.search(text) is not None else None


def _timer(match: re.Match[str]) -> SetTimer:
    count = match["count"]
    number = 1 if count is None else _NUMBERS.get(count.lower()) or int(count)
    about = (match["about"] or "").strip()
    return SetTimer(number * _SECONDS_IN[match["unit"].lower()], about)
