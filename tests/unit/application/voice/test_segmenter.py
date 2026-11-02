"""Нарезка речи на фразы (S-11.3): вероятности окон → события, время — по длительности окон."""

import pytest

from vtuber.application.voice import (
    BargeIn,
    Segmenter,
    SegmenterConfig,
    SpeechEnded,
    SpeechStarted,
)

WINDOW_MS = 32.0
CFG = SegmenterConfig(
    threshold=0.5,
    start_ms=96,
    end_silence_ms=320,
    barge_in_ms=320,
    pre_roll_ms=64,
    max_phrase_s=2.0,
)


def _feed(segmenter: Segmenter, probabilities: list[float], mark: bytes = b"x") -> list[object]:
    events: list[object] = []
    for probability in probabilities:
        events += segmenter.feed(mark, probability)
    return events


def test_short_noise_is_not_a_phrase() -> None:
    segmenter = Segmenter(CFG, WINDOW_MS)

    assert _feed(segmenter, [1, 1, 0, 1, 1, 0] * 3) == []
    assert not segmenter.in_phrase


def test_phrase_starts_after_start_ms_and_ends_after_silence() -> None:
    segmenter = Segmenter(CFG, WINDOW_MS)

    events = _feed(segmenter, [1.0] * 3)
    assert events == [SpeechStarted()]
    assert segmenter.in_phrase

    events = _feed(segmenter, [0.0] * 10)
    assert len(events) == 1
    assert isinstance(events[0], SpeechEnded)
    assert not segmenter.in_phrase


def test_pause_shorter_than_end_silence_keeps_the_phrase() -> None:
    segmenter = Segmenter(CFG, WINDOW_MS)
    _feed(segmenter, [1.0] * 3)

    assert _feed(segmenter, [0.0] * 5 + [1.0] + [0.0] * 5) == []
    assert segmenter.in_phrase


def test_barge_in_once_per_phrase_after_enough_speech() -> None:
    segmenter = Segmenter(CFG, WINDOW_MS)

    events = _feed(segmenter, [1.0] * 15)

    assert events == [SpeechStarted(), BargeIn()]


def test_short_phrase_does_not_barge_in() -> None:
    segmenter = Segmenter(CFG, WINDOW_MS)

    events = _feed(segmenter, [1.0] * 4 + [0.0] * 10)

    assert BargeIn() not in events


def test_pcm_keeps_pre_roll_and_drops_trailing_silence() -> None:
    segmenter = Segmenter(CFG, WINDOW_MS)
    _feed(segmenter, [0.0] * 5, b"s")
    _feed(segmenter, [1.0] * 4, b"v")

    (ended,) = _feed(segmenter, [0.0] * 10, b"t")

    assert isinstance(ended, SpeechEnded)
    assert ended.pcm.endswith(b"vvvv")
    assert ended.pcm.startswith(b"s")
    assert b"t" not in ended.pcm


def test_long_phrase_is_closed_by_force() -> None:
    segmenter = Segmenter(CFG, WINDOW_MS)

    events = _feed(segmenter, [1.0] * 70)

    assert any(isinstance(event, SpeechEnded) for event in events)


@pytest.mark.parametrize("probability", [0.49, 0.0])
def test_below_threshold_is_silence(probability: float) -> None:
    segmenter = Segmenter(CFG, WINDOW_MS)

    assert _feed(segmenter, [probability] * 20) == []
