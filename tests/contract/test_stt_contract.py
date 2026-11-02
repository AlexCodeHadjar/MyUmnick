"""Любые адаптеры VadPort и STTPort обязаны пройти эти тесты (R-57, принцип L)."""

import wave
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.fakes import FakeSTT, FakeVad
from vtuber.adapters.stt import SileroVad, VadConfig, WhisperConfig, WhisperSTT
from vtuber.domain import SAMPLE_WIDTH_BYTES, AudioChunk, AudioFormat, STTUnavailable
from vtuber.ports import STTPort, VadPort

ROOT = Path(__file__).resolve().parents[2]
VAD_MODEL = ROOT / "models" / "stt" / "vad" / "silero_vad.onnx"
WHISPER_DIR = ROOT / "models" / "stt" / "whisper-turbo"
SPEECH = ROOT / "tests" / "data" / "speech_ru_16k.wav"
SAMPLE_RATE = 16_000
SILENCE_MAX = 0.2
SPEECH_MIN = 0.5


def speech_pcm() -> bytes:
    """Запись Silero: «Привет, меня зовут Алексей, я живу в городе Казань»."""
    with wave.open(str(SPEECH), "rb") as wav:
        return wav.readframes(wav.getnframes())


@asynccontextmanager
async def _vad(path: Path) -> AsyncIterator[VadPort]:
    async with SileroVad(VadConfig(model_path=path, threads=1)) as vad:
        yield vad


def _whisper_cfg(path: Path) -> WhisperConfig:
    return WhisperConfig(
        model_dir=path,
        language="ru",
        device="cpu",
        compute_type="int8",
        threads=4,
        final_beam=1,
    )


@asynccontextmanager
async def _whisper(path: Path) -> AsyncIterator[STTPort]:
    async with WhisperSTT(_whisper_cfg(path)) as stt:
        yield stt


@dataclass(frozen=True, slots=True)
class VadCase:
    available: Callable[[], AbstractAsyncContextManager[VadPort]]
    unavailable: Callable[[], AbstractAsyncContextManager[VadPort]]


@dataclass(frozen=True, slots=True)
class SttCase:
    available: Callable[[], AbstractAsyncContextManager[STTPort]]
    unavailable: Callable[[], AbstractAsyncContextManager[STTPort]]
    expected: tuple[str, ...]


@pytest.fixture(
    params=[
        pytest.param(
            VadCase(lambda: nullcontext(FakeVad()), lambda: nullcontext(FakeVad(available=False))),
            id="fake",
        ),
        pytest.param(
            VadCase(lambda: _vad(VAD_MODEL), lambda: _vad(VAD_MODEL.parent / "нет.onnx")),
            id="silero",
            marks=pytest.mark.skipif(not VAD_MODEL.is_file(), reason="нет модели VAD (ADR-0016)"),
        ),
    ]
)
def vad_case(request: pytest.FixtureRequest) -> VadCase:
    return request.param  # type: ignore[no-any-return]  # pytest не типизирует param


@pytest.fixture(
    params=[
        pytest.param(
            SttCase(
                lambda: nullcontext(FakeSTT("меня зовут Алексей")),
                lambda: nullcontext(FakeSTT(available=False)),
                ("алексе",),
            ),
            id="fake",
        ),
        pytest.param(
            SttCase(
                lambda: _whisper(WHISPER_DIR),
                lambda: _whisper(WHISPER_DIR / "нет"),
                ("алексе", "казан"),
            ),
            id="whisper",
            marks=[
                pytest.mark.slow,
                pytest.mark.skipif(
                    not (WHISPER_DIR / "model.bin").is_file(), reason="нет модели (ADR-0016)"
                ),
            ],
        ),
    ]
)
def stt_case(request: pytest.FixtureRequest) -> SttCase:
    return request.param  # type: ignore[no-any-return]  # pytest не типизирует param


async def _probabilities(vad: VadPort, pcm: bytes) -> list[float]:
    step = vad.window_samples * SAMPLE_WIDTH_BYTES
    return [
        await vad.speech_probability(pcm[start : start + step])
        for start in range(0, len(pcm) - step + 1, step)
    ]


async def test_vad_tells_speech_from_silence(vad_case: VadCase) -> None:
    async with vad_case.available() as vad:
        silence = await _probabilities(vad, bytes(SAMPLE_RATE * SAMPLE_WIDTH_BYTES))
        vad.reset()
        speech = await _probabilities(vad, speech_pcm())

    assert max(silence) < SILENCE_MAX
    assert max(speech) > SPEECH_MIN
    assert vad.audio_format.sample_rate == SAMPLE_RATE


async def test_vad_rejects_wrong_window_size(vad_case: VadCase) -> None:
    async with vad_case.available() as vad:
        with pytest.raises(ValueError, match="окно VAD"):
            await vad.speech_probability(bytes(10))


async def test_unavailable_vad_raises_stt_unavailable(vad_case: VadCase) -> None:
    async with vad_case.unavailable() as vad:
        window = bytes(vad.window_samples * SAMPLE_WIDTH_BYTES)
        with pytest.raises(STTUnavailable):
            await vad.speech_probability(window)


@pytest.mark.parametrize("final", [False, True])
async def test_stt_recognizes_recorded_speech(stt_case: SttCase, final: bool) -> None:
    audio = AudioChunk(AudioFormat(SAMPLE_RATE), speech_pcm())
    async with stt_case.available() as stt:
        text = (await stt.transcribe(audio, final=final)).lower()

    for word in stt_case.expected:
        assert word in text


async def test_stt_empty_audio_is_empty_text(stt_case: SttCase) -> None:
    async with stt_case.available() as stt:
        assert await stt.transcribe(AudioChunk(AudioFormat(SAMPLE_RATE), b""), final=True) == ""


async def test_unavailable_stt_raises_stt_unavailable(stt_case: SttCase) -> None:
    audio = AudioChunk(AudioFormat(SAMPLE_RATE), bytes(320))
    async with stt_case.unavailable() as stt:
        with pytest.raises(STTUnavailable):
            await stt.transcribe(audio, final=True)
