"""Планировщик простоя (S-10.3, T-13): фон — только в простое, отмена — сразу при новом ходе."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from tests.fakes import FakeClock
from vtuber.application.scheduler import IdleJob, IdleScheduler, SchedulerConfig
from vtuber.domain import (
    CancelReason,
    GenerationFailed,
    TurnCancelled,
    TurnFinished,
    TurnId,
    TurnStarted,
)
from vtuber.kernel import EventBus

IDLE_AFTER_MS = 500


@dataclass(slots=True)
class _Time:
    """Сон планировщика двигает FakeClock: ожидание простоя — без настоящего времени."""

    clock: FakeClock = field(default_factory=FakeClock)
    slept: list[float] = field(default_factory=list)

    async def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.clock.advance_ms(seconds * 1000)
        await asyncio.sleep(0)


@dataclass(slots=True)
class _Job:
    """Задача, которая ждёт `release`; считает запуски, отмены и завершения."""

    name: str
    release: asyncio.Event = field(default_factory=asyncio.Event)
    starts: int = 0
    cancels: int = 0
    done: int = 0

    async def run(self) -> None:
        self.starts += 1
        try:
            await self.release.wait()
        except asyncio.CancelledError:
            self.cancels += 1
            raise
        self.done += 1

    def job(self) -> IdleJob:
        return IdleJob(self.name, self.run)


async def _settle() -> None:
    for _ in range(10):
        await asyncio.sleep(0)


@asynccontextmanager
async def _running(time: _Time) -> AsyncIterator[IdleScheduler]:
    scheduler = IdleScheduler(SchedulerConfig(idle_after_ms=IDLE_AFTER_MS), time.clock, time.sleep)
    loop = asyncio.create_task(scheduler.run())
    try:
        yield scheduler
    finally:
        loop.cancel()
        await asyncio.wait([loop])


async def test_job_waits_for_idle_period_then_runs() -> None:
    time, work = _Time(), _Job("факты")
    work.release.set()
    async with _running(time) as scheduler:
        scheduler.submit(work.job())
        await _settle()

    assert time.slept == [IDLE_AFTER_MS / 1000]
    assert work.done == 1
    assert scheduler.pending == 0


async def test_busy_postpones_jobs_until_idle_again() -> None:
    time, work = _Time(), _Job("резюме")
    work.release.set()
    async with _running(time) as scheduler:
        scheduler.busy()
        scheduler.submit(work.job())
        await _settle()
        assert work.starts == 0

        time.clock.advance_ms(10_000)
        scheduler.idle()
        await _settle()

    # Простой считается от конца хода, а не от старта планировщика.
    assert time.slept == [IDLE_AFTER_MS / 1000]
    assert work.done == 1


async def test_new_turn_cancels_running_job_at_once_and_it_retries_later() -> None:
    time, work = _Time(), _Job("индексация")
    async with _running(time) as scheduler:
        scheduler.submit(work.job())
        await _settle()
        assert work.starts == 1

        scheduler.busy()
        await asyncio.sleep(0)
        assert work.cancels == 1
        await _settle()
        assert scheduler.pending == 1

        work.release.set()
        scheduler.idle()
        await _settle()

    assert work.starts == 2
    assert work.done == 1
    assert scheduler.pending == 0


async def test_failed_job_does_not_stop_the_queue() -> None:
    time, after = _Time(), _Job("после")
    after.release.set()

    async def broken() -> None:
        msg = "кривой JSON от LLM"
        raise GenerationFailed(msg)

    async with _running(time) as scheduler:
        scheduler.submit(IdleJob("сломанная", broken))
        scheduler.submit(after.job())
        await _settle()

    assert after.done == 1
    assert scheduler.pending == 0


async def test_follows_turns_from_the_bus() -> None:
    time, bus, work = _Time(), EventBus(), _Job("факты")
    async with _running(time) as scheduler:
        scheduler.follow(bus)
        scheduler.submit(work.job())
        await _settle()
        assert work.starts == 1

        await bus.publish(TurnStarted(TurnId(1)))
        await _settle()
        assert work.cancels == 1

        work.release.set()
        await bus.publish(TurnCancelled(TurnId(1), CancelReason.USER_STOP))
        await _settle()
        assert work.done == 1

        await bus.publish(TurnStarted(TurnId(2)))
        await bus.publish(TurnFinished(TurnId(2)))
        await _settle()


async def test_stopping_the_scheduler_cancels_the_running_job() -> None:
    time, work = _Time(), _Job("долгая")
    async with _running(time) as scheduler:
        scheduler.submit(work.job())
        await _settle()
        assert work.starts == 1
    await _settle()

    assert work.cancels == 1
