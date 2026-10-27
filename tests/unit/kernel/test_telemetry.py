import asyncio
import io
import json
import time

import pytest

from tests.fakes import FakeClock
from vtuber.domain import MetricRecorded, TurnId
from vtuber.kernel import MAX_PENDING_METRICS, EventBus, Telemetry, TraceWriter, turn_context

SPAN_OVERHEAD_LIMIT_NS = 5_000


async def _published(telemetry: Telemetry, bus: EventBus, count: int) -> list[MetricRecorded]:
    received: list[MetricRecorded] = []
    done = asyncio.Event()

    async def collect(event: MetricRecorded) -> None:
        received.append(event)
        if len(received) == count:
            done.set()

    bus.subscribe(MetricRecorded, collect)
    runner = asyncio.create_task(telemetry.run())
    await asyncio.wait_for(done.wait(), timeout=1)
    runner.cancel()
    return received


async def test_span_measures_block_with_clock_and_reaches_bus() -> None:
    bus, clock = EventBus(), FakeClock()
    telemetry = Telemetry(bus, clock)

    with telemetry.span("llm.stream"):
        clock.advance_ms(120)

    assert await _published(telemetry, bus, 1) == [MetricRecorded("llm.stream", 120_000_000, None)]


async def test_metric_carries_current_turn() -> None:
    bus = EventBus()
    telemetry = Telemetry(bus, FakeClock())

    with turn_context(TurnId(9)):
        telemetry.record("llm.first_token", 210)

    [metric] = await _published(telemetry, bus, 1)
    assert metric.turn_id == TurnId(9)


def test_span_left_by_exception_records_nothing() -> None:
    telemetry = Telemetry(EventBus(), FakeClock())

    with pytest.raises(asyncio.CancelledError), telemetry.span("tts.phrase"):
        raise asyncio.CancelledError

    assert telemetry.pending == 0


def test_full_queue_drops_metrics_instead_of_failing() -> None:
    telemetry = Telemetry(EventBus(), FakeClock())

    for _ in range(MAX_PENDING_METRICS + 1):
        telemetry.record("x", 1)

    assert telemetry.pending == MAX_PENDING_METRICS


async def test_trace_writer_writes_one_json_line_per_metric() -> None:
    stream = io.StringIO()

    await TraceWriter(stream)(MetricRecorded("tts.phrase", 1500, TurnId(2)))

    assert json.loads(stream.getvalue()) == {"name": "tts.phrase", "ns": 1500, "turn_id": 2}


def test_perf_counter_resolves_microseconds() -> None:
    assert time.get_clock_info("perf_counter").resolution <= 1e-6


@pytest.mark.slow
def test_span_overhead_is_under_five_microseconds() -> None:
    spans = MAX_PENDING_METRICS // 2

    def per_span_ns() -> float:
        telemetry = Telemetry(EventBus())
        started = time.perf_counter_ns()
        for _ in range(spans):
            with telemetry.span("bench"):
                pass
        with_span = time.perf_counter_ns() - started
        started = time.perf_counter_ns()
        for _ in range(spans):
            pass
        empty = time.perf_counter_ns() - started
        return (with_span - empty) / spans

    best = min(per_span_ns() for _ in range(5))
    assert best < SPAN_OVERHEAD_LIMIT_NS, f"накладные расходы span: {best:.0f} нс"
