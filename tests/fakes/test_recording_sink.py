from tests.fakes import FakeClock, RecordingSink
from vtuber.domain import Emotion


async def test_records_everything_with_clock_time() -> None:
    clock = FakeClock()
    sink = RecordingSink(clock)

    await sink.emotion(Emotion.HAPPY)
    clock.advance_ms(5)
    await sink.text("При")
    await sink.text("вет")
    await sink.done()

    assert sink.kinds() == ["emotion", "text", "text", "done"]
    assert sink.shown_text() == "Привет"
    assert sink.emotions() == [Emotion.HAPPY]
    assert [entry.at_ns for entry in sink.entries] == [0, 5_000_000, 5_000_000, 5_000_000]
