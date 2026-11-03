"""Инициативные реплики на фейковых часах: срабатывание, отмена вводом, лимит (S-15.1)."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from vtuber.application.conversation import Initiative, InitiativeActions, InitiativeConfig


def _cfg(*, max_unanswered: int = 2, when_hidden: bool = False) -> InitiativeConfig:
    return InitiativeConfig(
        enabled=True,
        idle_after_s=10,
        max_unanswered=max_unanswered,
        when_hidden=when_hidden,
        poll_s=1,
    )


@dataclass(slots=True)
class _World:
    """Время идёт только через `advance`; `speak` может висеть, пока реплику не дослушают."""

    now: float = 0.0
    spoken: int = 0
    stopped: int = 0
    busy: bool = False
    hold_speech: bool = False
    speech_failure: Exception | None = None
    released: asyncio.Event = field(default_factory=asyncio.Event)
    tick: asyncio.Event = field(default_factory=asyncio.Event)

    def clock(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        wake_at = self.now + seconds
        while self.now < wake_at:
            await self.tick.wait()

    async def speak(self) -> None:
        self.spoken += 1
        if self.speech_failure is not None:
            raise self.speech_failure
        if self.hold_speech:
            await self.released.wait()

    async def stop(self) -> None:
        self.stopped += 1

    async def advance(self, seconds: float) -> None:
        for _ in range(int(seconds)):
            self.now += 1
            # Новое событие на каждый шаг: `wait()` у взведённого не уступает циклу и завис бы.
            passed, self.tick = self.tick, asyncio.Event()
            passed.set()
            await _settle()


async def _settle() -> None:
    for _ in range(10):
        await asyncio.sleep(0)


@asynccontextmanager
async def _running(world: _World, cfg: InitiativeConfig) -> AsyncIterator[Initiative]:
    actions = InitiativeActions(world.speak, world.stop, lambda: world.busy)
    initiative = Initiative(cfg, actions, world.clock, world.sleep)
    task = asyncio.create_task(initiative.run())
    await _settle()
    try:
        yield initiative
    finally:
        task.cancel()
        await asyncio.wait({task})


async def test_speaks_after_quiet_and_not_earlier() -> None:
    world = _World()
    async with _running(world, _cfg()):
        await world.advance(9)
        assert world.spoken == 0
        await world.advance(1)
        assert world.spoken == 1


async def test_limit_of_unanswered_lines_and_user_resets_it() -> None:
    world = _World()
    async with _running(world, _cfg(max_unanswered=2)) as initiative:
        await world.advance(100)
        assert world.spoken == 2
        initiative.user_input()
        await world.advance(10)
        assert world.spoken == 3


async def test_input_interrupts_speech_at_once() -> None:
    world = _World(hold_speech=True)
    async with _running(world, _cfg()) as initiative:
        await world.advance(10)
        assert world.spoken == 1
        assert world.stopped == 0
        initiative.user_input()
        await _settle()
        assert world.stopped == 1
        # Перебитая реплика не повторяется сразу: тишину считаем заново.
        world.hold_speech = False
        await world.advance(9)
        assert world.spoken == 1


async def test_finished_speech_is_not_stopped() -> None:
    world = _World()
    async with _running(world, _cfg()):
        await world.advance(10)
    assert (world.spoken, world.stopped) == (1, 0)


async def test_input_restarts_the_quiet() -> None:
    world = _World()
    async with _running(world, _cfg()) as initiative:
        await world.advance(9)
        initiative.user_input()
        await world.advance(9)
        assert world.spoken == 0


async def test_silent_while_busy_and_quiet_counts_from_the_end() -> None:
    world = _World(busy=True)
    async with _running(world, _cfg()):
        await world.advance(50)
        assert world.spoken == 0
        world.busy = False
        await world.advance(9)
        assert world.spoken == 0
        await world.advance(1)
        assert world.spoken == 1


async def test_hidden_window_stays_silent_and_return_restarts_the_quiet() -> None:
    world = _World()
    async with _running(world, _cfg()) as initiative:
        initiative.set_visible(visible=False)
        await world.advance(50)
        assert world.spoken == 0
        initiative.set_visible(visible=True)
        await world.advance(9)
        assert world.spoken == 0
        await world.advance(1)
        assert world.spoken == 1


async def test_hidden_window_can_be_allowed() -> None:
    world = _World()
    async with _running(world, _cfg(when_hidden=True)) as initiative:
        initiative.set_visible(visible=False)
        await world.advance(10)
        assert world.spoken == 1


async def test_failed_speech_does_not_stop_the_loop() -> None:
    world = _World(speech_failure=RuntimeError("нет модели"))
    async with _running(world, _cfg(max_unanswered=2)):
        await world.advance(30)
        assert world.spoken == 2
