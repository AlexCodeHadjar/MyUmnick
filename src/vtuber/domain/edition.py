"""Издание программы (Этап 20, ADR-0032): язык, персона, голос и своя память — набор настроек."""

from enum import StrEnum


class EditionId(StrEnum):
    """Издание выбирается до старта ядра: от него зависят файлы конфига и папка данных."""

    RU = "ru"
    EN = "en"


class ContentProfile(StrEnum):
    """Насколько персоне разрешено «всё» (ADR-0033); жёсткий минимум не зависит от профиля."""

    STANDARD = "standard"
    UNFILTERED = "unfiltered"
