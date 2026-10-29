"""Планировщик простоя (T-13): фоновые задачи — только когда пользователь не ждёт ответа.

Суммаризация, извлечение фактов, индексация памяти (S-10.4) нагружают LLM и CPU — во время хода
они отняли бы скорость у ответа. Поэтому задача ждёт `idle_after_ms` тишины после хода и
отменяется сразу, как начинается новый ход; отменённая задача встаёт в начало очереди и
повторяется в следующем простое — задачи обязаны быть перезапускаемыми.
"""

import asyncio
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import NoReturn

from pydantic import Field

from vtuber.domain import TurnCancelled, TurnFinished, TurnStarted
from vtuber.kernel import ConfigSection, EventBus, get_logger

NS_PER_S = 1_000_000_000
NS_PER_MS = 1_000_000

type Clock = Callable[[], int]
"""Монотонное время в наносекундах (`time.perf_counter_ns`)."""
type Sleep = Callable[[float], Awaitable[None]]

_log = get_logger(__name__)


class SchedulerConfig(ConfigSection):
    """`idle_after_ms` — сколько тишины после хода считать простоем."""

    idle_after_ms: int = Field(gt=0)


@dataclass(frozen=True, slots=True)
class IdleJob:
    """Фоновая задача: `run` можно звать повторно — отменённая задача перезапускается."""

    name: str
    run: Callable[[], Awaitable[None]]


class IdleScheduler:
    """Очередь фоновых задач, которые выполняются по одной и только в простое (T-13).

    `busy()` — пользователь ждёт ответа: текущая задача отменяется сразу (синхронно, в том же
    шаге цикла), новые не начинаются. `idle()` — ход закончился: через `idle_after_ms` без новых
    ходов очередь продолжается. Цикл — `run()`, задачей у владельца (bootstrap).
    """

    def __init__(
        self,
        cfg: SchedulerConfig,
        clock: Clock = time.perf_counter_ns,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._idle_after_ns = cfg.idle_after_ms * NS_PER_MS
        self._clock = clock
        self._sleep = sleep
        self._queue: deque[IdleJob] = deque()
        self._busy = False
        self._idle_since = clock()
        self._current: asyncio.Task[None] | None = None
        self._wake = asyncio.Event()

    @property
    def pending(self) -> int:
        """Задач в очереди (без выполняемой)."""
        return len(self._queue)

    def submit(self, job: IdleJob) -> None:
        """Поставить задачу в очередь; выполнится в ближайшем простое."""
        self._queue.append(job)
        self._wake.set()

    def busy(self) -> None:
        """Начался ход: отменить текущую задачу и не начинать новых до `idle()`."""
        self._busy = True
        if self._current is not None and not self._current.done():
            self._current.cancel()

    def idle(self) -> None:
        """Ход закончился: отсчёт простоя — с этого момента."""
        self._busy = False
        self._idle_since = self._clock()
        self._wake.set()

    def follow(self, bus: EventBus) -> None:
        """Ходы с шины: начало — `busy()`, конец или отмена — `idle()`."""

        async def started(_: TurnStarted) -> None:
            self.busy()

        async def ended(_: TurnFinished | TurnCancelled) -> None:
            self.idle()

        bus.subscribe(TurnStarted, started)
        bus.subscribe(TurnFinished, ended)
        bus.subscribe(TurnCancelled, ended)

    async def run(self) -> NoReturn:
        """Цикл планировщика; отмена цикла отменяет и текущую задачу."""
        try:
            while True:
                await self._wake.wait()
                self._wake.clear()
                await self._drain()
        finally:
            if self._current is not None:
                self._current.cancel()

    async def _drain(self) -> None:
        while self._queue and not self._busy:
            remaining_ns = self._idle_after_ns - (self._clock() - self._idle_since)
            if remaining_ns > 0:
                await self._sleep(remaining_ns / NS_PER_S)
                continue
            await self._execute(self._queue.popleft())

    async def _execute(self, job: IdleJob) -> None:
        task = asyncio.create_task(_call(job))
        self._current = task
        # wait, а не await: отмена задачи (busy) не должна отменять сам цикл планировщика.
        await asyncio.wait([task])
        self._current = None
        if task.cancelled():
            self._queue.appendleft(job)
            _log.info("idle.job_interrupted", job=job.name)
        elif (error := task.exception()) is not None:
            # R-42: верхняя граница фоновой задачи — сбой в лог, очередь живёт дальше.
            _log.warning("idle.job_failed", job=job.name, error=repr(error))
        else:
            _log.info("idle.job_done", job=job.name)


async def _call(job: IdleJob) -> None:
    """Задача — корутиной: `create_task` не принимает произвольный Awaitable."""
    await job.run()
