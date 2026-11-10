"""Что спрашивают: погода, новости, свежий факт или явный поиск (ADR-0036).

Правила по словам, без модели: обычная реплика проверяется за микросекунды и в сеть не уходит
(приоритет 1). Ошибка в сторону «не искать» стоит честного «не знаю», в сторону «искать» — пары
секунд ожидания, поэтому правила узкие: только явные слова о погоде, новостях и «сейчас».
"""

import re
from dataclasses import dataclass
from typing import Final, Literal

type Day = Literal["now", "today", "tomorrow"]


@dataclass(frozen=True, slots=True)
class Weather:
    """Погода в городе `city` (None — город по умолчанию из настроек) на `day`."""

    city: str | None
    day: Day


@dataclass(frozen=True, slots=True)
class News:
    """Свежие новости о `topic` (пусто — главные новости)."""

    topic: str


@dataclass(frozen=True, slots=True)
class Search:
    """Обычный поиск по запросу."""

    query: str


type Intent = Weather | News | Search

_FLAGS: Final = re.IGNORECASE | re.DOTALL
_EXPLICIT: Final = re.compile(
    r"\b(?:найди|поищи|загугли|посмотри|проверь)\s+в\s+(?:интернете|сети|гугле)\b[\s,:-]*(?P<a>.*)"
    r"|\b(?:поиск\s+в\s+интернете|в\s+интернете\s+найди)\b[\s,:-]*(?P<b>.*)"
    r"|\b(?:search|look\s+up|google)\s+(?:the\s+web|online|the\s+internet)?\s*(?:for\s+)?(?P<c>.+)",
    _FLAGS,
)
_WEATHER: Final = re.compile(
    r"\b(?:погод\w*|температур\w*|градус\w*|дожд\w*|снег\w*|прогноз\w*|weather|forecast"
    r"|temperature|raining|snowing)\b",
    _FLAGS,
)
_CITY: Final = re.compile(
    r"\b(?:в|во)\s+(?P<ru>[А-ЯЁ][а-яё-]+(?:\s+[А-ЯЁ][а-яё-]+)?)"
    r"|\b(?:in|for)\s+(?P<en>[A-Z][a-z-]+(?:\s+[A-Z][a-z-]+)?)",
)
_TOMORROW: Final = re.compile(r"\b(?:завтра|tomorrow)\b", _FLAGS)
_TODAY: Final = re.compile(r"\b(?:сегодня|today|tonight)\b", _FLAGS)
_NEWS: Final = re.compile(
    r"\b(?:новост\w*|что\s+(?:нового|случилось|произошло)|news|what(?:'s|\s+is)\s+new"
    r"|what\s+happened|headlines)\b",
    _FLAGS,
)
_NEWS_TOPIC: Final = re.compile(
    r"\b(?:новост\w*|news)\b\s*(?:о|об|про|по|about|on|in)?\s*(?P<topic>[^?.!]*)", _FLAGS
)
_FRESH: Final = re.compile(
    r"\b(?:курс\s+\w+|сколько\s+(?:сейчас\s+)?стоит|кто\s+(?:выиграл|победил)|счёт\s+матча"
    r"|exchange\s+rate|price\s+of|who\s+won|current\s+\w+|latest\s+\w+)\b",
    _FLAGS,
)
_TRIM: Final = " .!?,:;—-"


def explicit_query(text: str) -> str | None:
    """Запрос из явной просьбы «найди в интернете …»; без неё — None."""
    match = _EXPLICIT.search(text)
    if match is None:
        return None
    query = (match["a"] or match["b"] or match["c"] or "").strip(_TRIM)
    return query or None


def classify(text: str, *, auto: bool) -> Intent | None:
    """Намерение реплики; `auto=False` — только явная просьба (прежнее поведение, ADR-0022)."""
    query = explicit_query(text)
    intent: Intent | None = Search(query) if query else None
    if not auto:
        return intent
    if _WEATHER.search(text):
        intent = _weather(text)
    elif _NEWS.search(text):
        intent = _news(text)
    elif intent is None and _FRESH.search(text):
        intent = Search(text.strip(_TRIM))
    return intent


def _weather(text: str) -> Weather:
    match = _CITY.search(text)
    city = None if match is None else (match["ru"] or match["en"])
    day: Day = "tomorrow" if _TOMORROW.search(text) else "today" if _TODAY.search(text) else "now"
    return Weather(city, day)


def _news(text: str) -> News:
    match = _NEWS_TOPIC.search(text)
    topic = "" if match is None else match["topic"].strip(_TRIM)
    return News(topic)
