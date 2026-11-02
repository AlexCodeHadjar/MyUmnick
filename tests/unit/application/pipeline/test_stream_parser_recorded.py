"""StreamParser на записанных ответах настоящей модели (S-8.1, Gemma 4 12B HauhauCS, ADR-0004)."""

import json
from pathlib import Path

import pytest

from vtuber.application.pipeline import EmotionCue, StreamParser, TextDelta

DATA = Path(__file__).resolve().parents[3] / "data" / "recorded_replies_gemma4.json"
RECORDED: list[dict[str, str | list[str]]] = json.loads(DATA.read_text(encoding="utf-8"))
ALL_TAG = "<"


@pytest.mark.parametrize("chunk_size", [1, 3, 7, 1000])
@pytest.mark.parametrize("record", RECORDED, ids=lambda record: str(record["id"]))
def test_recorded_reply_parses_the_same_for_any_chunking(
    record: dict[str, str | list[str]], chunk_size: int
) -> None:
    reply = str(record["reply"])
    parser = StreamParser()
    events = []
    for start in range(0, len(reply), chunk_size):
        events.extend(parser.feed(reply[start : start + chunk_size]))
    events.extend(parser.flush())

    shown = "".join(e.text for e in events if isinstance(e, TextDelta))
    spoken = "".join(e.spoken_text for e in events)

    assert [e.emotion.value for e in events if isinstance(e, EmotionCue)] == record["emotions"]
    assert shown == record["shown"]
    assert ALL_TAG not in shown
    assert ALL_TAG not in spoken
