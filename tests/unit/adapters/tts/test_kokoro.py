from dataclasses import dataclass, field
from pathlib import Path

import pytest

from vtuber.adapters.tts import KokoroConfig, KokoroTTS, load_kokoro, to_pcm16
from vtuber.domain import GenerationFailed, TTSUnavailable

CFG = KokoroConfig(
    model_path=Path("models/tts/kokoro/test.onnx"),
    voices_path=Path("models/tts/kokoro/test.bin"),
    voice="af_heart",
    lang="en-us",
    speed=1.1,
    chunk_ms=100,
)


@dataclass
class FakeKokoro:
    """Kokoro без ONNX: 0.25 с тишины на фразу, вызовы запоминаются."""

    rate: int = 24000
    error: Exception | None = None
    calls: list[tuple[str, str, float, str]] = field(default_factory=list)

    def create(self, text: str, voice: str, speed: float, lang: str) -> tuple[object, int]:
        self.calls.append((text, voice, speed, lang))
        if self.error is not None:
            raise self.error
        return [0.5] * (self.rate // 4), self.rate


async def _synthesize(tts: KokoroTTS, phrase: str) -> list[bytes]:
    return [chunk.pcm async for chunk in tts.synthesize(phrase)]


async def test_phrase_is_split_into_chunks_after_warmup() -> None:
    engine = FakeKokoro()
    async with KokoroTTS(CFG, loader=lambda _m, _v: engine) as tts:
        chunks = await _synthesize(tts, "  Hello there!  ")

    # 0.25 с при 24 кГц = 6000 сэмплов → 2400 + 2400 + 1200, по 2 байта.
    assert [len(chunk) for chunk in chunks] == [4800, 4800, 2400]
    assert tts.audio_format.sample_rate == 24000
    assert engine.calls == [
        ("Hello.", "af_heart", 1.1, "en-us"),
        ("Hello there!", "af_heart", 1.1, "en-us"),
    ]


async def test_phrase_without_letters_is_silent() -> None:
    engine = FakeKokoro()
    async with KokoroTTS(CFG, loader=lambda _m, _v: engine) as tts:
        assert await _synthesize(tts, " … — ") == []


async def test_missing_files_make_engine_unavailable_with_hint() -> None:
    async with KokoroTTS(CFG) as tts:
        with pytest.raises(TTSUnavailable, match="kokoro-onnx"):
            await _synthesize(tts, "Hi")


async def test_engine_error_becomes_generation_failed() -> None:
    engine = FakeKokoro()
    async with KokoroTTS(CFG, loader=lambda _m, _v: engine) as tts:
        engine.error = RuntimeError("phonemizer")
        with pytest.raises(GenerationFailed, match="Kokoro"):
            await _synthesize(tts, "Hi")


async def test_wrong_sample_rate_fails_at_load() -> None:
    async with KokoroTTS(CFG, loader=lambda _m, _v: FakeKokoro(rate=22050)) as tts:
        with pytest.raises(TTSUnavailable, match="24000"):
            await _synthesize(tts, "Hi")


def test_pcm_conversion_clips_and_scales() -> None:
    assert to_pcm16([0.0, 1.0, -2.0]) == b"\x00\x00\xff\x7f\x01\x80"


def test_loader_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_kokoro(tmp_path / "none.onnx", tmp_path / "none.bin")
