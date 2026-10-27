from collections.abc import Sequence

from hypothesis import given
from hypothesis import strategies as st

from vtuber.application.pipeline import EmotionCue, ParseEvent, StreamParser, TextDelta
from vtuber.domain import Emotion


def _run(*deltas: str) -> tuple[StreamParser, list[ParseEvent]]:
    parser = StreamParser()
    events = [event for delta in deltas for event in parser.feed(delta)]
    return parser, events + parser.flush()


def _display(events: Sequence[ParseEvent]) -> str:
    return "".join(event.text for event in events if isinstance(event, TextDelta))


def _spoken(events: Sequence[ParseEvent]) -> str:
    return "".join(event.spoken_text for event in events)


def _emotions(events: Sequence[ParseEvent]) -> list[Emotion]:
    return [event.emotion for event in events if isinstance(event, EmotionCue)]


def test_plain_text_passes_through_immediately() -> None:
    parser = StreamParser()

    assert parser.feed("Привет, ") == [TextDelta("Привет, ", "Привет, ")]


def test_tag_becomes_emotion_cue_and_never_reaches_text() -> None:
    _, events = _run("<happy>Привет!")

    assert events == [EmotionCue(Emotion.HAPPY), TextDelta("Привет!", "Привет!")]


def test_tag_split_between_deltas_is_recognised() -> None:
    parser = StreamParser()

    assert parser.feed("Ой, <ha") == [TextDelta("Ой, ", "Ой, ")]
    assert parser.feed("ppy>ура") == [EmotionCue(Emotion.HAPPY), TextDelta("ура", "ура")]


def test_unknown_tag_is_dropped_from_display_and_speech() -> None:
    _, events = _run("Я <excited>рада")

    assert _display(events) == "Я рада"
    assert _emotions(events) == []


def test_tag_name_ignores_case_and_spaces() -> None:
    _, events = _run("< Sad >Жаль.")

    assert _emotions(events) == [Emotion.SAD]
    assert _display(events) == "Жаль."


def test_angle_brackets_that_are_not_tags_stay_in_text() -> None:
    for text in ("3 < 5 > 2", "а <б в", "x<y", "if a<b and c>d"):
        _, events = _run(text)
        assert _display(events) == text, text


def test_lone_angle_bracket_at_end_is_kept() -> None:
    _, events = _run("Меньше <")

    assert _display(events) == "Меньше <"


def test_unfinished_tag_at_end_of_stream_is_dropped() -> None:
    _, events = _run("Привет <hap")

    assert _display(events) == "Привет "


def test_too_long_tag_prefix_is_released_as_text() -> None:
    long_prefix = "<" + "a" * 40

    _, events = _run(long_prefix, " конец")

    assert _display(events) == long_prefix + " конец"


def test_speech_drops_emoji_and_markdown_but_chat_keeps_them() -> None:
    _, events = _run("**Ура** 🎉 #победа")

    assert _display(events) == "**Ура** 🎉 #победа"
    assert _spoken(events).split() == ["Ура", "победа"]


def test_full_text_keeps_known_tags_normalised_and_drops_unknown() -> None:
    parser, _ = _run("<Happy>Привет! <excited>Как <sad>жаль.")

    assert parser.full_text == "<happy>Привет! Как <sad>жаль."


_WORDS = st.text(alphabet="абв где жзи клм <>=3 ", max_size=8).map(
    lambda text: text.replace("<", "").replace(">", "")
)
_TAGS = st.sampled_from([emotion.tag for emotion in Emotion] + ["<unknown>", "<Happy>"])


@given(
    st.lists(st.tuples(_WORDS, _TAGS), max_size=12),
    _WORDS,
    st.lists(st.integers(min_value=1, max_value=7), min_size=1, max_size=40),
)
def test_any_split_gives_text_without_tags_and_all_known_emotions(
    pieces: list[tuple[str, str]], tail: str, cuts: list[int]
) -> None:
    raw = "".join(word + tag for word, tag in pieces) + tail
    deltas, position = [], 0
    for size in cuts * (len(raw) // len(cuts) + 1):
        if position >= len(raw):
            break
        deltas.append(raw[position : position + size])
        position += size

    _, events = _run(*deltas)

    assert _display(events) == "".join(word for word, _ in pieces) + tail
    known = [Emotion(tag.strip("<>").lower()) for _, tag in pieces if tag != "<unknown>"]
    assert _emotions(events) == known
