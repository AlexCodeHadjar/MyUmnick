"""Пение: команда, чтение записи, отмена, история (S-18.5)."""

import array
import asyncio
import wave
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

from tests.fakes import FakeClock, FakeLLM, RecordingSink
from tests.fakes.conversation import make_conversation
from vtuber.domain import AudioChunk, AudioFormat, GenerationFailed, PerformanceRequested
from vtuber.kernel import EventBus, PluginContext, Telemetry
from vtuber_singing import SingingConfig, SingingPlugin, is_playable, song_chunks, to_mono

RATE = 8000


def _song(path: Path, seconds: float = 0.5, channels: int = 1, width: int = 2) -> Path:
    with wave.open(str(path), "wb") as song:
        song.setnchannels(channels)
        song.setsampwidth(width)
        song.setframerate(RATE)
        song.writeframes(
            b"\x10\x00" * round(seconds * RATE) * channels if width == 2 else b"\0" * 8
        )
    return path


async def _plugin(folder: Path, bus: EventBus) -> PluginContext:
    ctx = PluginContext("singing", bus, {"songs_dir": str(folder)})
    await SingingPlugin().setup(ctx)
    return ctx


async def test_each_song_gets_a_command_and_bad_files_are_skipped(tmp_path: Path) -> None:
    _song(tmp_path / "Колыбельная.wav")
    (tmp_path / "битая.wav").write_bytes(b"not a wav")
    ctx = await _plugin(tmp_path, EventBus())
    assert set(ctx.commands) == {"спой колыбельная", "Спой колыбельная"}


async def test_command_asks_for_a_performance(tmp_path: Path) -> None:
    _song(tmp_path / "песня.wav")
    bus = EventBus()
    requested: list[str] = []

    async def on_request(event: PerformanceRequested) -> None:
        requested.append(event.title)
        await event.audio.aclose()

    bus.subscribe(PerformanceRequested, on_request)
    ctx = await _plugin(tmp_path, bus)
    await ctx.commands["спой песня"]()
    assert requested == ["песня"]


def test_only_16_bit_wav_is_playable(tmp_path: Path) -> None:
    assert is_playable(_song(tmp_path / "a.wav"))
    assert is_playable(_song(tmp_path / "b.wav", channels=2))
    assert not is_playable(_song(tmp_path / "c.wav", width=1))
    assert not is_playable(tmp_path / "нет.wav")


def test_stereo_becomes_mono() -> None:
    stereo = array.array("h", [100, 300, -100, -300]).tobytes()
    assert array.array("h", to_mono(stereo, 2)).tolist() == [200, -200]
    assert to_mono(b"\x01\x00", 1) == b"\x01\x00"


async def test_song_is_paced_with_a_lead(tmp_path: Path) -> None:
    path = _song(tmp_path / "a.wav", seconds=1.0)
    slept: list[float] = []

    async def sleep(seconds: float) -> None:
        slept.append(seconds)

    from vtuber_singing import _Pace  # noqa: PLC0415 — подмена часов только здесь

    cfg = SingingConfig(lead_s=0.5, chunk_ms=100)
    chunks = [c async for c in song_chunks(path, cfg, _Pace(lambda: 0.0, sleep))]
    assert sum(c.duration_s for c in chunks) == pytest.approx(1.0)
    assert slept, "звук сверх запаса должен ждать"
    assert slept[0] == pytest.approx(0.1)


async def test_broken_file_during_playback_is_a_generation_failure(tmp_path: Path) -> None:
    with pytest.raises(GenerationFailed, match="нет"):
        async for _ in song_chunks(tmp_path / "нет.wav", SingingConfig()):
            pass


async def _endless() -> AsyncGenerator[AudioChunk]:
    while True:
        yield AudioChunk(AudioFormat(RATE), b"\0\0" * 80)
        await asyncio.sleep(0.001)


async def _short() -> AsyncGenerator[AudioChunk]:
    yield AudioChunk(AudioFormat(RATE), b"\0\0" * 80)


def _service() -> tuple[FakeLLM, object]:
    bus = EventBus()
    llm = FakeLLM("Ответ.")
    return llm, make_conversation(llm, bus, Telemetry(bus, FakeClock()))


async def test_performance_plays_without_the_model_and_leaves_a_note() -> None:
    bus = EventBus()
    llm = FakeLLM("Ответ.")
    service = make_conversation(llm, bus, Telemetry(bus, FakeClock()))
    sink = RecordingSink()

    await service.perform("колыбельная", _short(), sink)
    await service.wait_idle()

    kinds = [entry.kind for entry in sink.entries]
    assert "audio" in kinds
    assert kinds[-1] == "done"
    assert llm.calls == []

    await service.handle("Понравилось?", RecordingSink())
    await service.wait_idle()
    assert any("колыбельная" in message.text for message in llm.calls[-1][0])


async def test_new_message_stops_the_song() -> None:
    bus = EventBus()
    llm = FakeLLM("Ответ.")
    service = make_conversation(llm, bus, Telemetry(bus, FakeClock()))
    sink = RecordingSink()
    await service.perform("бесконечная", _endless(), sink)
    await asyncio.sleep(0.02)

    await service.handle("Стой", RecordingSink())
    played = len(sink.entries)
    await asyncio.sleep(0.02)

    assert len(sink.entries) == played, "после отмены звука быть не должно"
    await service.wait_idle()
