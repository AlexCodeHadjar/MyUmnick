"""Проверки ответа для оценки качества: ключевые слова, отказ, длина, разметка, кириллица."""

import re
from typing import Final

from pydantic import BaseModel, ConfigDict

_TAG: Final = re.compile(r"<[a-z_]+>")
_SENTENCE_END: Final = re.compile(r"[.!?…]+")
_MARKDOWN: Final = re.compile(
    r"\*\*|__|`|^\s{0,3}#{1,6}\s|^\s*[-*•]\s|^\s*\d+[.)]\s|\[[^\]]+\]\([^)]+\)",
    re.MULTILINE,
)
_EMOJI: Final = re.compile("[\U0001f300-\U0001faff☀-➿️]")
_CYRILLIC: Final = re.compile("[а-яё]")
_LATIN: Final = re.compile("[a-z]")
REFUSAL_MARKERS: Final = (
    "не знаю",
    "не могу знать",
    "не могу сказать",
    "не могу этого знать",
    "понятия не имею",
    "не имею понятия",
    "без понятия",
    "не уверен",
    "не могу предсказать",
    "невозможно предсказать",
    "нельзя предсказать",
    "нет доступа",
    "не имею доступа",
    "не вижу",
    "не помню",
    "не в курсе",
    "откуда мне знать",
    "не рассказывал",
    "не говорил",
)


class Expect(BaseModel):
    """Что проверить в последнем ответе; незаданное поле — проверка не применяется."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    any_of: tuple[str, ...] = ()
    none_of: tuple[str, ...] = ()
    refusal: bool = False
    max_sentences: int | None = None
    no_markdown: bool = False
    min_cyrillic_ratio: float | None = None


def evaluate(expect: Expect, reply: str) -> list[str]:
    """Проблемы ответа (пусто — пройдено). Теги эмоций `<happy>` перед проверкой убираются."""
    text = _TAG.sub("", reply).strip()
    problems = (
        _any_of(expect.any_of, text),
        _none_of(expect.none_of, text),
        _refusal(expect.refusal, text),
        _sentences(expect.max_sentences, text),
        _markdown(expect.no_markdown, text),
        _cyrillic(expect.min_cyrillic_ratio, text),
    )
    return [problem for problem in problems if problem]


def contains_word(text: str, term: str) -> bool:
    """`term` с начала слова, без учёта регистра и ё — так проходят падежные формы.

    Число не совпадает с более длинным: «8» не находится в «80».
    """
    pattern = rf"(?<!\w){re.escape(_normalize(term))}"
    if term[-1].isdigit():
        pattern += r"(?!\d)"
    return re.search(pattern, _normalize(text)) is not None


def _normalize(text: str) -> str:
    return text.casefold().replace("ё", "е")


def _any_of(terms: tuple[str, ...], text: str) -> str | None:
    if not terms or any(contains_word(text, term) for term in terms):
        return None
    return f"нет ни одного из {list(terms)}"


def _none_of(terms: tuple[str, ...], text: str) -> str | None:
    found = [term for term in terms if contains_word(text, term)]
    return f"запрещённое {found}" if found else None


def _refusal(expected: bool, text: str) -> str | None:  # noqa: FBT001 — поле проверки
    if not expected or any(marker in _normalize(text) for marker in REFUSAL_MARKERS):
        return None
    return "ожидался честный отказ («не знаю»), а модель ответила"


def _sentences(limit: int | None, text: str) -> str | None:
    count = len([part for part in _SENTENCE_END.split(text) if part.strip()])
    if limit is None or count <= limit:
        return None
    return f"предложений {count} > {limit}"


def _markdown(forbidden: bool, text: str) -> str | None:  # noqa: FBT001 — поле проверки
    if forbidden and (_MARKDOWN.search(text) or _EMOJI.search(text)):
        return "разметка или эмодзи"
    return None


def _cyrillic(minimum: float | None, text: str) -> str | None:
    lowered = text.casefold()
    cyrillic, latin = len(_CYRILLIC.findall(lowered)), len(_LATIN.findall(lowered))
    ratio = cyrillic / (cyrillic + latin) if cyrillic + latin else 1.0
    if minimum is None or ratio >= minimum:
        return None
    return f"доля кириллицы {ratio:.2f} < {minimum}"
