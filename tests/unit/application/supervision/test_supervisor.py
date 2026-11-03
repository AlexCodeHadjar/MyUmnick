"""Наблюдатель на фейках: падение, зависание, предел попыток, успешный возврат."""

import asyncio
from collections.abc import AsyncGenerator

import pytest

from vtuber.application.supervision import (
    FailureFlag,
    Supervisor,
    SupervisorConfig,
    WatchedSTT,
    WatchedTTS,
)
from vtuber.domain import (
    AudioChunk,
    AudioFormat,
    BackendNotice,
    BackendState,
    BackendStatusChanged,
    Component,
    STTUnavailable,
    TTSUnavailable,
)
from vtuber.kernel import EventBus

FMT = AudioFormat(sample_rate=1000)
TICK_S = 0.001


def _cfg(**overrides: float) -> SupervisorConfig:
    values: dict[str, float | bool] = {
        "enabled": True,
        "check_s": TICK_S,
        "health_timeout_s": 0.02,
        "failures_to_restart": 2,
        "backoff_s": 1.0,
        "backoff_max_s": 4.0,
        "max_attempts": 3,
        "stable_s": 60.0,
        "voice_timeout_s": 1.0,
        "stt_timeout_s": 1.0,
    }
    return SupervisorConfig.model_validate({**values, **overrides})


class _Component:
    component = Component.LLM

    def __init__(self, *, restarts_ok: int = 99) -> None:
        self.alive = True
        self.hung = False
        self.checks = 0
        self.restarts = 0
        self._restarts_ok = restarts_ok

    async def healthy(self) -> bool:
        self.checks += 1
        if self.hung:
            await asyncio.Event().wait()
        return self.alive

    async def restart(self) -> None:
        self.restarts += 1
        if self.restarts > self._restarts_ok:
            raise TTSUnavailable("не поднялся")
        self.alive = True
        self.hung = False


class _World:
    def __init__(self, item: _Component, cfg: SupervisorConfig) -> None:
        self.item = item
        self.states: list[BackendState] = []
        self.notices: list[str] = []
        self.pauses: list[float] = []
        bus = EventBus()

        async def on_status(event: BackendStatusChanged) -> None:
            self.states.append(event.state)

        async def on_notice(event: BackendNotice) -> None:
            self.notices.append(event.text)

        async def sleep(seconds: float) -> None:
            if seconds != cfg.check_s:
                self.pauses.append(seconds)
            await asyncio.sleep(TICK_S)

        bus.subscribe(BackendStatusChanged, on_status)
        bus.subscribe(BackendNotice, on_notice)
        self.supervisor = Supervisor((item,), cfg, bus, sleep)

    async def run_for(self, seconds: float) -> None:
        running = asyncio.create_task(self.supervisor.run())
        await asyncio.sleep(seconds)
        running.cancel()
        await asyncio.gather(running, return_exceptions=True)


async def test_healthy_component_is_left_alone() -> None:
    world = _World(_Component(), _cfg())
    await world.run_for(0.1)
    assert world.item.restarts == 0
    assert world.states == []


async def test_crash_is_restarted_and_user_is_told() -> None:
    item = _Component()
    item.alive = False
    world = _World(item, _cfg())
    await world.run_for(0.4)
    assert item.restarts == 1
    assert world.states == [BackendState.LOADING, BackendState.READY]
    assert world.notices[0].startswith("Языковая модель: перезапускается")
    assert world.notices[-1] == "Языковая модель: снова работает"


async def test_hang_counts_as_a_failure() -> None:
    item = _Component()
    item.hung = True
    world = _World(item, _cfg())
    await world.run_for(0.5)
    assert item.restarts == 1
    assert world.states[-1] is BackendState.READY


async def test_one_bad_check_does_not_restart() -> None:
    item = _Component()
    world = _World(item, _cfg(failures_to_restart=1000))
    item.alive = False
    await world.run_for(0.1)
    assert item.restarts == 0


async def test_limit_of_attempts_with_growing_pause_then_clear_failure() -> None:
    item = _Component(restarts_ok=0)
    item.alive = False
    world = _World(item, _cfg())
    await world.run_for(0.5)
    assert item.restarts == 3
    assert world.pauses == [1.0, 2.0, 4.0]
    assert world.states[-1] is BackendState.FAILED
    assert "нужен перезапуск приложения" in world.notices[-1]


async def test_pause_never_exceeds_the_maximum() -> None:
    item = _Component(restarts_ok=0)
    item.alive = False
    world = _World(item, _cfg(max_attempts=5, backoff_max_s=3.0))
    await world.run_for(0.8)
    assert world.pauses == [1.0, 2.0, 3.0, 3.0, 3.0]


async def test_component_that_returns_by_itself_is_reported() -> None:
    item = _Component(restarts_ok=0)
    item.alive = False
    world = _World(item, _cfg())
    running = asyncio.create_task(world.supervisor.run())
    await asyncio.sleep(0.5)
    assert world.states[-1] is BackendState.FAILED
    item.alive = True
    await asyncio.sleep(0.2)
    running.cancel()
    await asyncio.gather(running, return_exceptions=True)
    assert world.states[-1:] == [BackendState.READY]


async def test_restart_loop_is_limited_even_when_each_restart_succeeds() -> None:
    item = _Component()

    class _Flapping(_Component):
        async def restart(self) -> None:
            item.restarts += 1

    flapping = _Flapping()
    flapping.alive = False
    world = _World(flapping, _cfg())
    await world.run_for(1.0)
    # Рестарт «успешен», но компонент тут же снова падает: цикл не должен быть бесконечным.
    assert item.restarts == 3
    assert world.states[-1] is BackendState.FAILED


class _Tts:
    def __init__(self, mode: str) -> None:
        self.mode = mode

    @property
    def audio_format(self) -> AudioFormat:
        return FMT

    async def synthesize(self, phrase: str) -> AsyncGenerator[AudioChunk]:
        if self.mode == "down":
            raise TTSUnavailable("нет модели")
        if self.mode == "hang":
            await asyncio.Event().wait()
        yield AudioChunk(FMT, b"\x00\x00")


async def _spoken(watched: WatchedTTS) -> list[AudioChunk]:
    return [chunk async for chunk in watched.synthesize("Привет")]


async def test_working_voice_passes_through_without_failure() -> None:
    flag = FailureFlag()
    assert len(await _spoken(WatchedTTS(_Tts("ok"), flag, 1.0))) == 1
    assert not flag.failed


@pytest.mark.parametrize("mode", ["down", "hang"])
async def test_broken_voice_raises_and_raises_the_flag(mode: str) -> None:
    flag = FailureFlag()
    with pytest.raises(TTSUnavailable):
        await _spoken(WatchedTTS(_Tts(mode), flag, 0.01))
    assert flag.failed


class _Stt:
    def __init__(self, mode: str) -> None:
        self.mode = mode

    async def transcribe(self, audio: AudioChunk, *, final: bool) -> str:
        if self.mode == "down":
            raise STTUnavailable("нет модели")
        if self.mode == "hang":
            await asyncio.Event().wait()
        return "текст"


@pytest.mark.parametrize("mode", ["down", "hang"])
async def test_broken_stt_raises_and_raises_the_flag(mode: str) -> None:
    flag = FailureFlag()
    watched = WatchedSTT(_Stt(mode), flag, 0.01)
    with pytest.raises(STTUnavailable):
        await watched.transcribe(AudioChunk(FMT, b"\x00\x00"), final=True)
    assert flag.failed


async def test_working_stt_passes_through() -> None:
    flag = FailureFlag()
    watched = WatchedSTT(_Stt("ok"), flag, 1.0)
    assert await watched.transcribe(AudioChunk(FMT, b"\x00\x00"), final=True) == "текст"
    assert not flag.failed
