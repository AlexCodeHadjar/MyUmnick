"""Звуки вокруг на фейках: событие, тишина, частота, не перебивать ведущего (S-14.4)."""

import array
import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from vtuber.application.voice import REACTIONS, SoundActions, SoundsConfig, SoundWatcher, loudness
from vtuber.domain import AudioChunk, AudioFormat, GenerationFailed, SoundHeard, SoundKind
from vtuber.kernel import EventBus

RATE = AudioFormat(16_000)
CFG = SoundsConfig(
    enabled=True,
    window_s=0.1,
    gate_rms=0.02,
    min_gap_s=60.0,
    react_to=(SoundKind.LAUGHTER, SoundKind.APPLAUSE),
)


def _audio(*, loud: bool = True) -> AudioChunk:
    count = round(0.1 * RATE.sample_rate)
    return AudioChunk(RATE, array.array("h", [8000 if loud else 0] * count).tobytes())


@dataclass(slots=True)
class _World:
    kind: SoundKind | None = SoundKind.LAUGHTER
    failure: Exception | None = None
    busy: bool = False
    now: float = 0.0
    calls: int = 0
    said: list[str] = field(default_factory=list)
    heard: list[SoundKind] = field(default_factory=list)

    async def classify(self, audio: AudioChunk) -> SoundKind | None:
        del audio
        self.calls += 1
        if self.failure is not None:
            raise self.failure
        return self.kind

    async def react(self, text: str) -> None:
        self.said.append(text)


async def _settle() -> None:
    for _ in range(50):
        await asyncio.sleep(0)


@asynccontextmanager
async def _running(world: _World) -> AsyncIterator[SoundWatcher]:
    bus = EventBus()

    async def on_sound(event: SoundHeard) -> None:
        world.heard.append(event.kind)

    bus.subscribe(SoundHeard, on_sound)
    actions = SoundActions(world.react, lambda: world.busy)
    watcher = SoundWatcher(CFG, world, bus, actions, lambda: world.now)
    task = asyncio.create_task(watcher.run())
    try:
        yield watcher
    finally:
        task.cancel()
        await asyncio.wait({task})


async def _hear(watcher: SoundWatcher, *, loud: bool = True) -> None:
    watcher.feed(_audio(loud=loud))
    await _settle()


def test_loudness_of_silence_and_sound() -> None:
    assert loudness(b"") == 0.0
    assert loudness(_audio(loud=False).pcm) == 0.0
    assert 0.2 < loudness(_audio().pcm) < 0.3


async def test_sound_becomes_event_and_reaction() -> None:
    world = _World()
    async with _running(world) as watcher:
        await _hear(watcher)
    assert world.heard == [SoundKind.LAUGHTER]
    assert world.said == [REACTIONS[SoundKind.LAUGHTER]]


async def test_silence_does_not_reach_the_model() -> None:
    world = _World()
    async with _running(world) as watcher:
        await _hear(watcher, loud=False)
    assert world.calls == 0


async def test_reaction_is_rare_but_events_keep_coming() -> None:
    world = _World()
    async with _running(world) as watcher:
        await _hear(watcher)
        await _hear(watcher)
        assert len(world.heard) == 2
        assert len(world.said) == 1
        world.now = 61.0
        await _hear(watcher)
    assert len(world.said) == 2


async def test_only_chosen_sounds_get_a_reaction() -> None:
    world = _World(kind=SoundKind.COUGH)
    async with _running(world) as watcher:
        await _hear(watcher)
    assert world.heard == [SoundKind.COUGH]
    assert world.said == []


async def test_nothing_runs_while_busy() -> None:
    world = _World(busy=True)
    async with _running(world) as watcher:
        await _hear(watcher)
    assert world.calls == 0
    assert world.said == []


async def test_host_speaking_after_classification_is_not_interrupted() -> None:
    world = _World()

    async def classify_then_busy(audio: AudioChunk) -> SoundKind | None:
        del audio
        world.busy = True
        return SoundKind.LAUGHTER

    bus = EventBus()
    actions = SoundActions(world.react, lambda: world.busy)
    watcher = SoundWatcher(CFG, _Classifier(classify_then_busy), bus, actions, lambda: world.now)
    task = asyncio.create_task(watcher.run())
    await _hear(watcher)
    task.cancel()
    await asyncio.wait({task})
    assert world.said == []


@dataclass(slots=True)
class _Classifier:
    call: object

    async def classify(self, audio: AudioChunk) -> SoundKind | None:
        assert callable(self.call)
        result: SoundKind | None = await self.call(audio)
        return result


async def test_failed_model_does_not_stop_the_watcher() -> None:
    world = _World(failure=GenerationFailed("нет модели"))
    async with _running(world) as watcher:
        await _hear(watcher)
        world.failure = None
        await _hear(watcher)
    assert world.heard == [SoundKind.LAUGHTER]


async def test_no_sound_means_no_event() -> None:
    world = _World(kind=None)
    async with _running(world) as watcher:
        await _hear(watcher)
    assert (world.heard, world.said) == ([], [])
