import itertools

import pytest
from hypothesis import given
from hypothesis import strategies as st

from vtuber.application.pipeline import ChunkerConfig, SentenceChunker

CFG = ChunkerConfig(first_min_words=4, next_min_words=10, max_words=25)


def _chunk(text: str, cfg: ChunkerConfig = CFG) -> list[str]:
    """Весь текст одной дельтой + хвост."""
    chunker = SentenceChunker(cfg)
    phrases = list(chunker.feed(text))
    if tail := chunker.flush():
        phrases.append(tail)
    return phrases


def _chunk_by_pieces(text: str, cuts: list[int], cfg: ChunkerConfig = CFG) -> list[str]:
    """Тот же текст, побитый на дельты в позициях `cuts`."""
    chunker = SentenceChunker(cfg)
    bounds = [0, *sorted({c for c in cuts if 0 < c < len(text)}), len(text)]
    phrases = [p for a, b in itertools.pairwise(bounds) for p in chunker.feed(text[a:b])]
    if tail := chunker.flush():
        phrases.append(tail)
    return phrases


def test_first_phrase_is_cut_after_four_words_at_comma() -> None:
    text = "Ну что ж, раз уж ты спрашиваешь, расскажу тебе одну историю про кота"

    assert _chunk(text)[:2] == [
        "Ну что ж, раз уж ты спрашиваешь,",
        "расскажу тебе одну историю про кота",
    ]


def test_first_phrase_is_not_cut_at_comma_before_four_words() -> None:
    assert _chunk("Да, конечно, сейчас всё будет")[0] == "Да, конечно, сейчас всё будет"


def test_next_phrases_need_more_words_before_comma() -> None:
    # После первой фразы запятая режет только после 10 слов: «пять шесть,» — ещё рано.
    text = "Раз два три четыре, пять шесть, семь восемь девять десять 11 12 13 14, конец"

    assert _chunk(text) == [
        "Раз два три четыре,",
        "пять шесть, семь восемь девять десять 11 12 13 14,",
        "конец",
    ]


def test_hard_stops_cut_regardless_of_length() -> None:
    assert _chunk("Привет! Как дела? Отлично… А ты.") == [
        "Привет!",
        "Как дела?",
        "Отлично…",
        "А ты.",
    ]


@pytest.mark.parametrize(
    "text",
    [
        "Число 3.5 не режется на точке",
        "Это значит, т.е. ничего не значит",
        "Яблоки, груши и т.д. лежат в корзине",
        "Автор — А. С. Пушкин, великий поэт",
    ],
)
def test_dots_inside_phrase_do_not_cut(text: str) -> None:
    no_soft_cuts = ChunkerConfig(first_min_words=50, next_min_words=50, max_words=50)

    assert _chunk(text, no_soft_cuts) == [text]


def test_ellipsis_of_three_dots_cuts_once_after_last_dot() -> None:
    assert _chunk("Подождите... ещё немного") == ["Подождите...", "ещё немного"]


def test_closing_quotes_and_brackets_stay_with_phrase() -> None:
    assert _chunk("Она сказала: «Привет!» И ушла (навсегда.) Вот.") == [
        "Она сказала: «Привет!»",
        "И ушла (навсегда.)",
        "Вот.",
    ]


def test_newline_always_cuts() -> None:
    assert _chunk("Первая строка\nвторая строка") == ["Первая строка", "вторая строка"]


def test_long_text_without_punctuation_is_cut_by_word_limit() -> None:
    words = " ".join(f"слово{i}" for i in range(12))

    assert _chunk(words, ChunkerConfig(first_min_words=4, next_min_words=10, max_words=5)) == [
        "слово0 слово1 слово2 слово3 слово4",
        "слово5 слово6 слово7 слово8 слово9",
        "слово10 слово11",
    ]


def test_stop_at_end_of_delta_waits_for_next_char() -> None:
    chunker = SentenceChunker(CFG)

    assert list(chunker.feed("Привет!")) == []
    assert list(chunker.feed(" Как")) == ["Привет!"]
    assert chunker.flush() == "Как"
    assert chunker.flush() is None


# Слова, знаки и пробелы вперемешку: всё, на чём нарезка может ошибиться.
_PIECES = st.sampled_from(
    ["слово", "т.е.", "3.5", "А.", ",", ".", "!", "?", "…", "...", "»", "«", "—", " ", "  ", "\n"]
)
_TEXT = st.lists(_PIECES, max_size=60).map("".join)


@given(_TEXT, st.lists(st.integers(min_value=1, max_value=200), max_size=30))
def test_result_does_not_depend_on_delta_boundaries(text: str, cuts: list[int]) -> None:
    assert _chunk_by_pieces(text, cuts) == _chunk(text)


@given(_TEXT)
def test_phrases_join_back_into_input_up_to_whitespace(text: str) -> None:
    phrases = _chunk(text, ChunkerConfig(first_min_words=2, next_min_words=3, max_words=4))

    assert all(phrase == phrase.strip() and phrase for phrase in phrases)
    assert " ".join(" ".join(phrases).split()) == " ".join(text.split())
