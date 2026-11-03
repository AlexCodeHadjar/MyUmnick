"""Что поднимает наблюдатель: голос, слух, сервер, состав списка (S-17.1)."""

import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path
from types import TracebackType
from typing import Self

import pytest

from tests.fakes import FakeClock
from tests.llm_stub import LLMStub
from vtuber.adapters.llm import LlamaServerConfig, LlamaServerProcess
from vtuber.application.supervision import FailureFlag
from vtuber.bootstrap.container import Core
from vtuber.bootstrap.supervision import LlmSupervised, TtsSupervised
from vtuber.bootstrap.voice_input import _LazyVoice
from vtuber.domain import (
    AudioChunk,
    AudioFormat,
    BackendState,
    BackendStatusChanged,
    LLMUnavailable,
    TTSUnavailable,
)
from vtuber.kernel import EventBus, Telemetry

FMT = AudioFormat(sample_rate=1000)


class _Engine:
    def __init__(self, *, loads_ok: bool = True) -> None:
        self.loads = 0
        self.unloads = 0
        self.loads_ok = loads_ok
        self.loaded = False

    async def __aenter__(self) -> Self:
        self.loads += 1
        self.loaded = self.loads_ok
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.unloads += 1
        self.loaded = False

    @property
    def audio_format(self) -> AudioFormat:
        return FMT

    async def synthesize(self, phrase: str) -> AsyncGenerator[AudioChunk]:
        if not self.loaded:
            raise TTSUnavailable("модель не загрузилась")
        yield AudioChunk(FMT, b"\x00\x00")


async def test_voice_is_reloaded_and_checked_before_flag_clears() -> None:
    engine = _Engine()
    flag = FailureFlag()
    flag.fail()
    item = TtsSupervised(engine, flag)
    assert not await item.healthy()

    await item.restart()

    assert (engine.unloads, engine.loads) == (1, 1)
    assert await item.healthy()


async def test_voice_that_does_not_load_stays_failed() -> None:
    flag = FailureFlag()
    flag.fail()
    item = TtsSupervised(_Engine(loads_ok=False), flag)
    with pytest.raises(TTSUnavailable):
        await item.restart()
    assert not await item.healthy()


def _server_cfg(tmp_path: Path, *, autostart: bool) -> LlamaServerConfig:
    return LlamaServerConfig(
        autostart=autostart,
        executable=tmp_path / "нет.exe",
        model=tmp_path / "нет.gguf",
        log_file=tmp_path / "llama.log",
        context_size=1024,
        slots=2,
        ready_timeout_s=1,
        stop_timeout_s=1,
        extra_args=(),
    )


async def test_server_without_a_model_is_not_supervised(tmp_path: Path) -> None:
    async with LlamaServerProcess(_server_cfg(tmp_path, autostart=True), "http://x") as server:
        assert not server.started


async def test_server_restart_reports_warmup_problem(tmp_path: Path) -> None:
    async def warm() -> str | None:
        return "модель не отвечает"

    async with (
        LLMStub("Ок") as stub,
        LlamaServerProcess(_server_cfg(tmp_path, autostart=False), stub.url) as server,
    ):
        with pytest.raises(LLMUnavailable, match="не отвечает"):
            await LlmSupervised(server, warm).restart()


class _Events:
    async def barge_in(self) -> None:
        await asyncio.sleep(0)


def _hearing(states: list[BackendState]) -> _LazyVoice:
    bus = EventBus()

    async def on_status(event: BackendStatusChanged) -> None:
        states.append(event.state)

    bus.subscribe(BackendStatusChanged, on_status)
    core = Core(bus, Telemetry(bus, FakeClock()))
    return _LazyVoice(None, _Events(), core, 1.0)  # type: ignore[arg-type]


async def test_crashed_hearing_is_reported_and_restart_runs_it_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs: list[int] = []

    async def listen(self: _LazyVoice) -> None:
        runs.append(1)
        if len(runs) == 1:
            raise RuntimeError
        await asyncio.Event().wait()

    monkeypatch.setattr(_LazyVoice, "_listen", listen)
    states: list[BackendState] = []
    voice = _hearing(states)

    await voice.on_frame(AudioChunk(FMT, b"\x00\x00"))
    await asyncio.sleep(0.01)
    assert not await voice.healthy()
    assert states == [BackendState.FAILED]

    await voice.restart()
    await asyncio.sleep(0.01)
    assert await voice.healthy()
    assert len(runs) == 2
    await voice.stop()
