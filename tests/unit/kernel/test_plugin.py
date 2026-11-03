import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest

from vtuber.domain import ConfigError, TurnFinished, TurnId
from vtuber.kernel import MAX_PENDING_PLUGIN_EVENTS, ConfigSection, EventBus, PluginContext


class _Section(ConfigSection):
    label: str


EVENT = TurnFinished(TurnId(1))


@asynccontextmanager
async def _running(ctx: PluginContext) -> AsyncIterator[None]:
    pump = asyncio.create_task(ctx.run())
    try:
        yield
    finally:
        pump.cancel()
        await asyncio.gather(pump, return_exceptions=True)


async def _drain() -> None:
    for _ in range(5):
        await asyncio.sleep(0)


async def test_slow_handler_does_not_hold_publisher() -> None:
    bus = EventBus()
    ctx = PluginContext("slow", bus, {})
    release = asyncio.Event()
    seen: list[TurnFinished] = []

    async def handler(event: TurnFinished) -> None:
        await release.wait()
        seen.append(event)

    ctx.subscribe(TurnFinished, handler)
    async with _running(ctx):
        # Обработчик заблокирован, а publish обязан вернуться: иначе плагин задержит ход.
        await asyncio.wait_for(bus.publish(EVENT), timeout=1)
        assert seen == []
        release.set()
        await _drain()
    assert seen == [EVENT]


async def test_handlers_run_one_at_a_time_in_order() -> None:
    bus = EventBus()
    ctx = PluginContext("order", bus, {})
    log: list[str] = []

    async def handler(event: TurnFinished) -> None:
        log.append(f"start {event.turn_id}")
        await asyncio.sleep(0)
        log.append(f"end {event.turn_id}")

    ctx.subscribe(TurnFinished, handler)
    async with _running(ctx):
        await bus.publish(TurnFinished(TurnId(1)))
        await bus.publish(TurnFinished(TurnId(2)))
        await _drain()
    assert log == ["start 1", "end 1", "start 2", "end 2"]


async def test_handler_error_does_not_stop_later_events() -> None:
    bus = EventBus()
    ctx = PluginContext("broken", bus, {})
    seen: list[TurnId] = []

    async def handler(event: TurnFinished) -> None:
        seen.append(event.turn_id)
        if len(seen) == 1:
            raise RuntimeError

    ctx.subscribe(TurnFinished, handler)
    async with _running(ctx):
        await bus.publish(TurnFinished(TurnId(1)))
        await bus.publish(TurnFinished(TurnId(2)))
        await _drain()
    assert seen == [TurnId(1), TurnId(2)]


async def test_overflow_drops_new_events_and_keeps_publisher_going() -> None:
    bus = EventBus()
    ctx = PluginContext("stuck", bus, {})
    seen: list[TurnFinished] = []

    async def handler(event: TurnFinished) -> None:
        seen.append(event)

    ctx.subscribe(TurnFinished, handler)
    for _ in range(MAX_PENDING_PLUGIN_EVENTS + 10):
        await bus.publish(EVENT)
    async with _running(ctx):
        await _drain()
        await asyncio.sleep(0.01)
    assert len(seen) == MAX_PENDING_PLUGIN_EVENTS


async def test_closed_context_ignores_events() -> None:
    bus = EventBus()
    ctx = PluginContext("closed", bus, {})
    seen: list[TurnFinished] = []

    async def handler(event: TurnFinished) -> None:
        seen.append(event)

    ctx.subscribe(TurnFinished, handler)
    ctx.close()
    async with _running(ctx):
        await bus.publish(EVENT)
        await _drain()
    assert seen == []


def test_settings_are_validated_by_plugin_model() -> None:
    bus = EventBus()
    assert PluginContext("a", bus, {"label": "x"}).settings(_Section).label == "x"
    with pytest.raises(ConfigError, match=r"plugins\.settings\.b"):
        PluginContext("b", bus, {"typo": "x"}).settings(_Section)
