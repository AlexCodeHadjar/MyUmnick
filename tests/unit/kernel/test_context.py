import asyncio
import io
import json
from collections.abc import Iterator

import pytest
import structlog

from vtuber.domain import TurnId
from vtuber.kernel import LoggingConfig, configure_logging, current_turn, get_logger, turn_context


@pytest.fixture
def stream() -> Iterator[io.StringIO]:
    output = io.StringIO()
    configure_logging(LoggingConfig(level="INFO"), output)
    yield output
    structlog.reset_defaults()
    structlog.contextvars.clear_contextvars()


def test_current_turn_is_set_only_inside_block() -> None:
    assert current_turn() is None
    with turn_context(TurnId(3)):
        assert current_turn() == TurnId(3)
    assert current_turn() is None


def test_logs_carry_turn_id_only_inside_block(stream: io.StringIO) -> None:
    log = get_logger("tests")
    with turn_context(TurnId(42)):
        log.info("turn.started")
    log.info("idle")

    inside, outside = (json.loads(line) for line in stream.getvalue().splitlines())
    assert inside["turn_id"] == 42
    assert "turn_id" not in outside


async def test_tasks_created_inside_block_inherit_turn() -> None:
    async def read() -> TurnId | None:
        return current_turn()

    with turn_context(TurnId(5)):
        task = asyncio.create_task(read())

    assert await task == TurnId(5)
