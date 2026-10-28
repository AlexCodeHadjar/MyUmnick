import asyncio
import threading
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import torch

from vtuber.adapters.tts import SileroConfig, SileroModel, SileroTTS, to_pcm
from vtuber.domain import GenerationFailed, TTSUnavailable

CFG = SileroConfig(
    model_path=Path("models/tts/silero/test.pt"),
    speaker="xenia",
    sample_rate=8000,
    threads=1,
    chunk_ms=100,
)


@dataclass
class FakeModel:
    """Модель Silero без torch.package: тон заданной длины, запоминает вызовы."""

    seconds: float = 0.25
    error: Exception | None = None
    calls: list[tuple[str, str, int]] = field(default_factory=list)

    def apply_tts(self, *, text: str, speaker: str, sample_rate: int) -> torch.Tensor:
        self.calls.append((text, speaker, sample_rate))
        if self.error is not None:
            raise self.error
        return torch.full((round(self.seconds * sample_rate),), 0.5)


async def _synthesize(tts: SileroTTS, phrase: str) -> list[bytes]:
    return [chunk.pcm async for chunk in tts.synthesize(phrase)]


async def test_phrase_is_split_into_chunks_of_configured_length() -> None:
    model = FakeModel(seconds=0.25)
    async with SileroTTS(CFG, loader=lambda _: model) as tts:
        chunks = await _synthesize(tts, "  Привет!  ")

    assert tts.audio_format.sample_rate == 8000
    # 0.25 с при 8 кГц = 2000 сэмплов → 800 + 800 + 400, по 2 байта.
    assert [len(chunk) for chunk in chunks] == [1600, 1600, 800]
    assert model.calls == [("Привет!", "xenia", 8000)]


async def test_phrase_without_letters_gives_no_audio() -> None:
    model = FakeModel()
    async with SileroTTS(CFG, loader=lambda _: model) as tts:
        assert await _synthesize(tts, " … — ") == []
    assert model.calls == []


async def test_missing_model_file_means_unavailable_with_download_hint() -> None:
    def missing(path: Path) -> SileroModel:
        raise FileNotFoundError(path)

    async with SileroTTS(CFG, loader=missing) as tts:
        with pytest.raises(TTSUnavailable, match=r"v5_6_ru\.pt"):
            await _synthesize(tts, "Привет")


async def test_broken_model_file_means_unavailable() -> None:
    def broken(path: Path) -> SileroModel:
        raise RuntimeError("not a zip archive")

    async with SileroTTS(CFG, loader=broken) as tts:
        with pytest.raises(TTSUnavailable, match="not a zip archive"):
            await _synthesize(tts, "Привет")


async def test_outside_context_manager_is_unavailable() -> None:
    with pytest.raises(TTSUnavailable, match="async with"):
        await _synthesize(SileroTTS(CFG, loader=lambda _: FakeModel()), "Привет")


async def test_synthesis_error_becomes_generation_failed() -> None:
    model = FakeModel(error=ValueError("bad symbol"))
    async with SileroTTS(CFG, loader=lambda _: model) as tts:
        with pytest.raises(GenerationFailed, match="bad symbol"):
            await _synthesize(tts, "Привет")


async def test_synthesis_runs_off_the_event_loop_and_is_serialized() -> None:
    threads: list[str] = []
    active = 0
    overlapped = False
    lock = threading.Lock()

    class SlowModel:
        def apply_tts(self, *, text: str, speaker: str, sample_rate: int) -> torch.Tensor:
            nonlocal active, overlapped
            threads.append(threading.current_thread().name)
            with lock:
                active += 1
                overlapped = overlapped or active > 1
            threading.Event().wait(0.05)
            with lock:
                active -= 1
            return torch.zeros(80)

    async with SileroTTS(CFG, loader=lambda _: SlowModel()) as tts:
        await asyncio.gather(_synthesize(tts, "Раз"), _synthesize(tts, "Два"))

    assert threading.main_thread().name not in threads
    assert not overlapped


def test_to_pcm_clamps_and_encodes_little_endian() -> None:
    pcm = to_pcm(torch.tensor([0.0, 1.0, -1.0, 2.0, -3.0]))

    assert pcm == bytes.fromhex("0000ff7f0180ff7f0180")
