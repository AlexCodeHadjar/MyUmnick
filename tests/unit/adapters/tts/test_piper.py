import asyncio
import threading
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from vtuber.adapters.tts import PiperConfig, PiperTTS, PiperVoiceLike, load_voice
from vtuber.domain import GenerationFailed, TTSUnavailable

CFG = PiperConfig(
    model_path=Path("models/tts/piper/test.onnx"),
    sample_rate=16000,
    length_scale=1.1,
    chunk_ms=100,
)


@dataclass
class Chunk:
    audio_int16_bytes: bytes


@dataclass
class FakeVoice:
    """Голос Piper без ONNX: по предложению — фрагмент заданной длины, вызовы запоминаются."""

    rate: int = 16000
    seconds_per_sentence: float = 0.15
    error: Exception | None = None
    calls: list[tuple[str, float]] = field(default_factory=list)

    @property
    def sample_rate(self) -> int:
        return self.rate

    def synthesize_chunks(self, text: str, length_scale: float) -> Iterable[Chunk]:
        self.calls.append((text, length_scale))
        if self.error is not None:
            raise self.error
        sentences = max(1, text.count(".") + text.count("!") + text.count("?"))
        samples = round(self.seconds_per_sentence * self.rate)
        return [Chunk(b"\x01\x00" * samples) for _ in range(sentences)]


async def _synthesize(tts: PiperTTS, phrase: str) -> list[bytes]:
    return [chunk.pcm async for chunk in tts.synthesize(phrase)]


async def test_sentences_are_joined_and_resplit_into_chunks() -> None:
    voice = FakeVoice()
    async with PiperTTS(CFG, loader=lambda _: voice) as tts:
        chunks = await _synthesize(tts, "  Раз. Два!  ")

    # Два предложения × 0.15 с при 16 кГц = 4800 сэмплов → 1600 + 1600 + 1600, по 2 байта.
    assert [len(chunk) for chunk in chunks] == [3200, 3200, 3200]
    assert tts.audio_format.sample_rate == 16000
    # Первый вызов — прогрев при загрузке (T-06); темп речи — из конфига.
    assert voice.calls == [("Привет.", 1.1), ("Раз. Два!", 1.1)]


async def test_phrase_without_letters_gives_no_audio() -> None:
    voice = FakeVoice()
    async with PiperTTS(CFG, loader=lambda _: voice) as tts:
        assert await _synthesize(tts, " … — ") == []
    assert len(voice.calls) == 1


async def test_missing_voice_means_unavailable_with_download_hint(tmp_path: Path) -> None:
    cfg = CFG.model_copy(update={"model_path": tmp_path / "нет.onnx"})
    async with PiperTTS(cfg) as tts:
        with pytest.raises(TTSUnavailable, match="piper-voices"):
            await _synthesize(tts, "Привет")


async def test_sample_rate_mismatch_means_unavailable() -> None:
    async with PiperTTS(CFG, loader=lambda _: FakeVoice(rate=22050)) as tts:
        with pytest.raises(TTSUnavailable, match="22050"):
            await _synthesize(tts, "Привет")


async def test_any_engine_error_on_load_means_unavailable() -> None:
    class OrtError(Exception):
        """Как pybind-исключения onnxruntime: не наследник RuntimeError."""

    def broken(path: Path) -> PiperVoiceLike:
        raise OrtError("INVALID_PROTOBUF")

    async with PiperTTS(CFG, loader=broken) as tts:
        with pytest.raises(TTSUnavailable, match="INVALID_PROTOBUF"):
            await _synthesize(tts, "Привет")


async def test_outside_context_manager_is_unavailable() -> None:
    with pytest.raises(TTSUnavailable, match="async with"):
        await _synthesize(PiperTTS(CFG, loader=lambda _: FakeVoice()), "Привет")


async def test_synthesis_error_becomes_generation_failed() -> None:
    voice = FakeVoice()
    async with PiperTTS(CFG, loader=lambda _: voice) as tts:
        voice.error = KeyError("phoneme")
        with pytest.raises(GenerationFailed, match="phoneme"):
            await _synthesize(tts, "Привет")


async def test_synthesis_runs_off_the_event_loop_and_is_serialized() -> None:
    names: list[str] = []
    active = 0
    overlapped = False
    lock = threading.Lock()

    class SlowVoice(FakeVoice):
        def synthesize_chunks(self, text: str, length_scale: float) -> Iterable[Chunk]:
            nonlocal active, overlapped
            names.append(threading.current_thread().name)
            with lock:
                active += 1
                overlapped = overlapped or active > 1
            threading.Event().wait(0.05)
            with lock:
                active -= 1
            return [Chunk(b"\x00\x00" * 80)]

    async with PiperTTS(CFG, loader=lambda _: SlowVoice()) as tts:
        await asyncio.gather(_synthesize(tts, "Раз"), _synthesize(tts, "Два"))

    assert threading.main_thread().name not in names
    assert not overlapped


def test_load_voice_requires_the_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_voice(tmp_path / "нет.onnx")
