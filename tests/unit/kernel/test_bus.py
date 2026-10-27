import asyncio
from dataclasses import dataclass

import pytest

from vtuber.kernel import EventBus


@dataclass(frozen=True)
class _Ping:
    value: int


@dataclass(frozen=True)
class _Pong:
    value: int


@dataclass(frozen=True)
class _LoudPing(_Ping):
    pass


async def test_handler_receives_only_events_of_its_type() -> None:
    bus, pings = EventBus(), list[_Ping]()

    async def on_ping(event: _Ping) -> None:
        pings.append(event)

    bus.subscribe(_Ping, on_ping)
    await bus.publish(_Ping(1))
    await bus.publish(_Pong(2))

    assert pings == [_Ping(1)]


async def test_dispatch_is_by_exact_type_not_subclass() -> None:
    bus, pings = EventBus(), list[_Ping]()

    async def on_ping(event: _Ping) -> None:
        pings.append(event)

    bus.subscribe(_Ping, on_ping)
    await bus.publish(_LoudPing(1))

    assert pings == []


async def test_publish_without_subscribers_does_nothing() -> None:
    await EventBus().publish(_Ping(1))


async def test_handlers_run_concurrently() -> None:
    bus, order = EventBus(), list[str]()
    released = asyncio.Event()

    async def slow(_: _Ping) -> None:
        await released.wait()
        order.append("slow")

    async def fast(_: _Ping) -> None:
        order.append("fast")
        released.set()

    bus.subscribe(_Ping, slow)
    bus.subscribe(_Ping, fast)
    await bus.publish(_Ping(1))

    assert order == ["fast", "slow"]


async def test_failing_handler_does_not_stop_others_or_publisher() -> None:
    bus, delivered = EventBus(), list[int]()

    async def broken(_: _Ping) -> None:
        raise RuntimeError("plugin bug")

    async def healthy(event: _Ping) -> None:
        delivered.append(event.value)

    bus.subscribe(_Ping, broken)
    bus.subscribe(_Ping, healthy)
    await bus.publish(_Ping(7))

    assert delivered == [7]


async def test_cancellation_raised_by_handler_is_not_swallowed() -> None:
    bus = EventBus()

    async def cancelled(_: _Ping) -> None:
        raise asyncio.CancelledError

    bus.subscribe(_Ping, cancelled)

    with pytest.raises(asyncio.CancelledError):
        await bus.publish(_Ping(1))


async def test_cancelling_publish_cancels_handlers() -> None:
    bus, started, cancelled = EventBus(), asyncio.Event(), asyncio.Event()

    async def waiting(_: _Ping) -> None:
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise

    bus.subscribe(_Ping, waiting)
    task = asyncio.create_task(bus.publish(_Ping(1)))
    await started.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert cancelled.is_set()
