import pytest

from vtuber.domain import MAX_TAG_LENGTH, Emotion, parse_tag


def test_tag_wraps_emotion_name_in_angle_brackets() -> None:
    assert Emotion.HAPPY.tag == "<happy>"


@pytest.mark.parametrize("emotion", list(Emotion), ids=str)
def test_every_emotion_tag_parses_back(emotion: Emotion) -> None:
    assert parse_tag(emotion.tag) is emotion


def test_tag_parsing_ignores_case_and_inner_spaces() -> None:
    assert parse_tag("<Happy>") is Emotion.HAPPY
    assert parse_tag("< sad >") is Emotion.SAD


@pytest.mark.parametrize("text", ["<unknown>", "happy", "<happy", "happy>", "<>", ""])
def test_unknown_or_malformed_tag_gives_none(text: str) -> None:
    assert parse_tag(text) is None


def test_max_tag_length_fits_longest_tag() -> None:
    longest = max(len(emotion.tag) for emotion in Emotion)

    assert longest == MAX_TAG_LENGTH


def test_emotion_names_are_lowercase_ascii_words() -> None:
    for emotion in Emotion:
        assert emotion.value.isascii()
        assert emotion.value.isalpha()
        assert emotion.value.islower()
