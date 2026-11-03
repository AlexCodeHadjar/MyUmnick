"""Теги жестов: не попадают в текст и речь, частота ограничена, неизвестный не ломает (S-18.4)."""

from vtuber.application.pipeline import (
    EmotionCue,
    GestureCue,
    ParseEvent,
    StreamParser,
    TextDelta,
)
from vtuber.domain import Emotion, Gesture, parse_gesture


def _parse(*deltas: str) -> tuple[list[ParseEvent], StreamParser]:
    parser = StreamParser()
    events = [event for delta in deltas for event in parser.feed(delta)]
    return [*events, *parser.flush()], parser


def _shown(events: list[ParseEvent]) -> str:
    return "".join(event.text for event in events if isinstance(event, TextDelta))


def _spoken(events: list[ParseEvent]) -> str:
    return "".join(event.spoken_text for event in events)


def test_gesture_tag_is_an_event_not_text_or_speech() -> None:
    events, parser = _parse("<happy><nod>Конечно!")
    assert events[:2] == [EmotionCue(Emotion.HAPPY), GestureCue(Gesture.NOD)]
    assert _shown(events) == "Конечно!"
    assert _spoken(events) == "Конечно!"
    assert parser.full_text == "<happy><nod>Конечно!"


def test_tag_split_between_deltas_is_held_until_closed() -> None:
    events, _ = _parse("Ну <no", "d>да")
    assert GestureCue(Gesture.NOD) in events
    assert _shown(events) == "Ну да"


def test_cut_gesture_tag_at_the_end_is_dropped() -> None:
    events, _ = _parse("Да <sta")
    assert _shown(events) == "Да "


def test_unknown_gesture_does_not_break_the_reply() -> None:
    events, parser = _parse("<dance>Ура!")
    assert _shown(events) == "Ура!"
    assert not [event for event in events if isinstance(event, GestureCue)]
    assert parser.full_text == "Ура!"


def test_gestures_too_close_are_dropped_from_events_and_history() -> None:
    events, parser = _parse("<nod>Да.<shake>Нет.<tilt>Ну.")
    assert [e.gesture for e in events if isinstance(e, GestureCue)] == [Gesture.NOD]
    assert parser.full_text == "<nod>Да.Нет.Ну."


def test_gesture_returns_after_enough_text() -> None:
    long = "Это достаточно длинная фраза для второго жеста."
    events, _ = _parse(f"<nod>{long}<tilt>Правда?")
    assert [e.gesture for e in events if isinstance(e, GestureCue)] == [Gesture.NOD, Gesture.TILT]


def test_emotion_tags_are_not_limited() -> None:
    events, _ = _parse("<happy>Да<sad>Нет<angry>Ну")
    assert len([event for event in events if isinstance(event, EmotionCue)]) == 3


def test_parse_gesture_ignores_case_and_spaces() -> None:
    assert parse_gesture("< NOD >") is Gesture.NOD
    assert parse_gesture("<happy>") is None
    assert parse_gesture("nod") is None
