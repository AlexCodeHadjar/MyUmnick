import io
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
import structlog

from vtuber.kernel import LoggingConfig, configure_logging, get_logger


@pytest.fixture
def stream() -> Iterator[io.StringIO]:
    output = io.StringIO()
    configure_logging(LoggingConfig(level="INFO", file=Path("logs/app.jsonl")), output)
    yield output
    structlog.reset_defaults()


def _records(stream: io.StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in stream.getvalue().splitlines()]


MODULE_LOGGER = get_logger("taken.at.import")  # как `_log` в модулях: до configure_logging


def test_each_event_is_one_json_line_with_level_time_and_module(stream: io.StringIO) -> None:
    get_logger("tests").info("model.loaded", seconds=4.2)

    [record] = _records(stream)
    assert record["event"] == "model.loaded"
    assert record["level"] == "info"
    assert record["module"] == "tests"
    assert record["seconds"] == 4.2
    assert "timestamp" in record


def test_events_below_configured_level_are_dropped(stream: io.StringIO) -> None:
    log = get_logger("tests")
    log.debug("token", text="При")
    log.warning("ttfa.over_budget")

    assert [record["event"] for record in _records(stream)] == ["ttfa.over_budget"]


def test_logger_taken_before_configuration_writes_to_configured_stream(
    stream: io.StringIO,
) -> None:
    MODULE_LOGGER.info("chat.ready")

    [record] = _records(stream)
    assert record["module"] == "taken.at.import"


def test_cyrillic_is_written_readable(stream: io.StringIO) -> None:
    get_logger("tests").info("ответ", text="Привет")

    assert "Привет" in stream.getvalue()
