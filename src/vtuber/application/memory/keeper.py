"""Фоновая работа памяти по ходам (T-13): факты и резюме — задачами планировщика простоя.

Ход не ждёт память: `TurnRemembered` только ставит задачи в очередь, а выполняются они, когда
пользователь молчит, и прерываются его новой репликой.
"""

from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from vtuber.application.memory.facts import FactMemory
from vtuber.application.memory.short_term import ShortTermMemory
from vtuber.application.memory.summarizer import Summarizer
from vtuber.application.memory.viewer_filter import without_viewer_turns
from vtuber.application.scheduler import IdleJob, IdleScheduler
from vtuber.domain import Message, TurnRemembered
from vtuber.kernel import EventBus, get_logger

type Now = Callable[[], datetime]

_log = get_logger(__name__)


class MemoryKeeper:
    """По каждому записанному ходу: факты — в долговременную память, отрезанное — в резюме."""

    def __init__(
        self,
        scheduler: IdleScheduler,
        history: ShortTermMemory,
        summarizer: Summarizer,
        facts: FactMemory,
    ) -> None:
        self._scheduler = scheduler
        self._history = history
        self._summarizer = summarizer
        self._facts = facts
        self.now: Now = lambda: datetime.now(UTC)

    def follow(self, bus: EventBus) -> None:
        """Подписка на `TurnRemembered`."""
        bus.subscribe(TurnRemembered, self.on_turn)

    async def on_turn(self, event: TurnRemembered) -> None:
        """Ставит задачи хода: сначала резюме (оно меняет промпт), затем факты."""
        turn, when = event.turn, self.now()
        dropped = without_viewer_turns(event.dropped)
        if dropped:
            self._scheduler.submit(IdleJob(f"summary:{turn.id}", lambda: self._summarize(dropped)))
        if not turn.is_external:
            self._scheduler.submit(IdleJob(f"facts:{turn.id}", lambda: self._learn(event, when)))

    async def _summarize(self, dropped: Sequence[Message]) -> None:
        summary = await self._summarizer.summarize(self._history.summary, dropped)
        self._history.set_summary(summary)
        _log.info("memory.summary_updated", chars=len(summary), dropped=len(dropped))

    async def _learn(self, event: TurnRemembered, when: datetime) -> None:
        await self._facts.learn(event.turn, when)
