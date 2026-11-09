"""Жёсткий минимум (Этап 20, ADR-0033): что не разрешено ни в одном профиле содержания.

Дешёвый входной фильтр — до вызова LLM, микросекунды: сочетание явных маркеров несовершеннолетия
и сексуального содержания в одной реплике. Ловит только явное (как и защита стрима, FR-31);
остальное держит правило в рамке промпта. Ошибка в сторону отказа стоит одного хода, а не беды.
"""

import re
import unicodedata
from typing import Final

_MINOR: Final = re.compile(
    r"\b(child\w*|kids?|minors?|underage\w*|under-?age|preteens?|pre-teens?|toddlers?|infants?"
    r"|loli\w*|shota\w*|schoolchild\w*|little (girl|boy)s?|middle school\w*|under ?18"
    r"|(?:i'?m|i am|you'?re|you are|she is|he is) (?:[1-9]|1[0-7])(?! ?(?:%|kg|cm|ft))"
    r"|(?:[1-9]|1[0-7])[- ]?(?:yo|y/o|years?[- ]old)"
    r"|ребён\w*|ребен\w*|дет(?:и|ей|ям|ьми|ях|ск\w*)|малолет\w*|несовершеннолет\w*|подрост\w*"
    r"|школьни\w*|лоли\w*|(?:[1-9]|1[0-7]) ?(?:лет|год\w*))\b",
    re.IGNORECASE,
)
_SEXUAL: Final = re.compile(
    r"\b(sex\w*|nude\w*|naked|porn\w*|erotic\w*|fuck\w*|horny|lewd|nsfw|orgasm\w*|genital\w*"
    r"|undress\w*|molest\w*|rape\w*|flirt\w*|talk\w* dirty|dirty talk\w*|"
    r"флирт\w*|секс\w*|эрот\w*|порн\w*|гол(?:ая|ый|ые|ой)|раздет\w*"
    r"|раздева\w*|трах\w*|интим\w*|возбужд\w*|изнасил\w*|растл\w*)\b",
    re.IGNORECASE,
)


def crosses_hard_floor(text: str) -> bool:
    """Реплика явно просит сексуальное содержание с участием несовершеннолетних."""
    plain = unicodedata.normalize("NFKC", text)
    return bool(_MINOR.search(plain) and _SEXUAL.search(plain))
