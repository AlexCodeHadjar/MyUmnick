"""Телеметрия: замер стадий хода и доставка метрик в шину и файл трасс."""

import asyncio
import contextlib
import json
import time
from collections.abc import Callable
from types import TracebackType
from typing import Final, NoReturn, Self, TextIO

from vtuber.domain import MetricRecorded
from vtuber.kernel.bus import EventBus
from vtuber.kernel.context import current_turn

MAX_PENDING_METRICS: Final = 4096
"""Предел очереди метрик: если `run` не успевает, лишние метрики отбрасываются, а не копятся."""

type Clock = Callable[[], int]


class Telemetry:
    """Замеряет стадии хода и отдаёт метрики в шину фоновой задачей `run`.

    Запись метрики синхронная и дешёвая — `put_nowait` в очередь, поэтому `span` можно ставить
    в горячий путь (R-08); публикация в шину — в `run`, вне горячего пути. Вызывать только из
    потока event loop: очередь asyncio не потокобезопасна.
    """

    def __init__(self, bus: EventBus, clock: Clock = time.perf_counter_ns) -> None:
        self._bus = bus
        self._clock = clock
        self._pending: asyncio.Queue[MetricRecorded] = asyncio.Queue(MAX_PENDING_METRICS)

    @property
    def pending(self) -> int:
        """Сколько метрик ждёт публикации."""
        return self._pending.qsize()

    def span(self, name: str) -> "Span":
        """Замер блока `with`; метрика пишется только при нормальном выходе (не при отмене)."""
        return Span(name, self._clock, self.record)

    def record(self, name: str, duration_ns: int) -> None:
        """Записывает готовый замер, например TTFT от начала хода; turn_id — текущий ход."""
        # Метрика не важнее хода: при переполненной очереди она теряется, ход продолжается.
        with contextlib.suppress(asyncio.QueueFull):
            self._pending.put_nowait(MetricRecorded(name, duration_ns, current_turn()))

    async def run(self) -> NoReturn:
        """Публикует метрики в шину, пока задачу не отменят (владелец — TaskGroup в bootstrap)."""
        while True:
            await self._bus.publish(await self._pending.get())


class Span:
    """Контекстный менеджер одного замера; создаётся `Telemetry.span`."""

    __slots__ = ("_clock", "_name", "_record", "_started_ns")

    def __init__(self, name: str, clock: Clock, record: Callable[[str, int], None]) -> None:
        self._name = name
        self._clock = clock
        self._record = record
        self._started_ns = 0

    def __enter__(self) -> Self:
        self._started_ns = self._clock()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is None:
            self._record(self._name, self._clock() - self._started_ns)


class TraceWriter:
    """Подписчик шины: пишет каждую метрику JSON-строкой в поток (`logs/traces.jsonl`).

    Поток открывает и закрывает bootstrap; буферизация — его же (без flush на каждую метрику).
    """

    def __init__(self, stream: TextIO) -> None:
        self._stream = stream

    async def __call__(self, event: MetricRecorded) -> None:
        """Пишет одну строку `{"name", "ns", "turn_id"}`."""
        line = json.dumps({"name": event.name, "ns": event.duration_ns, "turn_id": event.turn_id})
        self._stream.write(line + "\n")
