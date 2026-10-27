import io
import json
from collections.abc import Iterator

import pytest
import structlog

from vtuber.domain import TurnId
from vtuber.kernel import LoggingConfig, configure_logging, get_logger, turn_context


@pytest.fixture
def stream() -> Iterator[io.StringIO]:
    output = io.StringIO()
    configure_logging(LoggingConfig(level="INFO"), output)
    yield output
    structlog.reset_defaults()
    structlog.contextvars.clear_contextvars()


def _records(stream: io.StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in stream.getvalue().splitlines()]


def test_each_event_is_one_json_line_with_level_time_and_logger(stream: io.StringIO) -> None:
    get_logger("tests").info("model.loaded", seconds=4.2)

    [record] = _records(stream)
    assert record["event"] == "model.loaded"
    assert record["level"] == "info"
    assert record["logger"] == "tests"
    assert record["seconds"] == 4.2
    assert "timestamp" in record


def test_events_below_configured_level_are_dropped(stream: io.StringIO) -> None:
    log = get_logger("tests")
    log.debug("token", text="При")
    log.warning("ttfa.over_budget")

    assert [record["event"] for record in _records(stream)] == ["ttfa.over_budget"]


def test_turn_context_adds_turn_id_only_inside_block(stream: io.StringIO) -> None:
    log = get_logger("tests")
    with turn_context(TurnId(42)):
        log.info("turn.started")
    log.info("idle")

    inside, outside = _records(stream)
    assert inside["turn_id"] == 42
    assert "turn_id" not in outside


def test_cyrillic_is_written_readable(stream: io.StringIO) -> None:
    get_logger("tests").info("ответ", text="Привет")

    assert "Привет" in stream.getvalue()
