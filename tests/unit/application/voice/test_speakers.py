"""Разделение собеседников на фейках: метка, короткая фраза, сбой, ответ не ждёт (S-14.3)."""

import array
import asyncio
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from tests.fakes import FakeSTT, FakeVad
from tools.eval_speakers import Heard, error_rate, person_of, render
from vtuber.adapters.stt.speaker_embedding import SherpaSpeakerEmbedder, SpeakerModelConfig
from vtuber.application.voice import (
    AddressedEvents,
    SegmenterConfig,
    SpeakerLabeler,
    SpeakersConfig,
    SpeakerTracker,
    VoiceConfig,
    VoiceListener,
    labelled,
)
from vtuber.domain import AudioChunk, AudioFormat, GenerationFailed, STTUnavailable

RATE = AudioFormat(16_000)
MODEL = Path(__file__).resolve().parents[4] / "models/stt/speakers/eres2net_base_3dspeaker_16k.onnx"
ANNA = (1.0, 0.0, 0.0)
ANNA_AGAIN = (0.9, 0.1, 0.0)
BORIS = (0.0, 1.0, 0.0)
CFG = SpeakersConfig(enabled=True, threshold=0.55, min_phrase_s=0.3, max_speakers=2, wait_s=0.05)
SEGMENTS = SegmenterConfig(
    threshold=0.5,
    start_ms=96,
    end_silence_ms=320,
    barge_in_ms=300,
    pre_roll_ms=64,
    max_phrase_s=20.0,
)


def _audio(seconds: float = 0.6, *, loud: bool = True) -> AudioChunk:
    count = round(seconds * RATE.sample_rate)
    return AudioChunk(RATE, array.array("h", [8000 if loud else 0] * count).tobytes())


@dataclass(slots=True)
class _Embedder:
    voices: list[tuple[float, ...]] = field(default_factory=list)
    failure: Exception | None = None
    delay_s: float = 0.0

    async def embed(self, audio: AudioChunk) -> tuple[float, ...]:
        del audio
        await asyncio.sleep(self.delay_s)
        if self.failure is not None:
            raise self.failure
        return self.voices.pop(0)


def test_tracker_separates_voices_and_recognizes_them_again() -> None:
    tracker = SpeakerTracker(0.55, 4)
    assert [tracker.identify(v) for v in (ANNA, BORIS, ANNA_AGAIN, BORIS)] == [1, 2, 1, 2]
    assert tracker.count == 2


def test_tracker_goes_to_the_nearest_when_there_is_no_room() -> None:
    tracker = SpeakerTracker(0.55, 2)
    tracker.identify(ANNA)
    tracker.identify(BORIS)
    assert tracker.identify((0.0, 0.3, 1.0)) == 2
    assert tracker.count == 2


async def test_no_label_while_only_one_voice_is_heard() -> None:
    labeler = SpeakerLabeler(CFG, _Embedder([ANNA, ANNA_AGAIN, BORIS, ANNA]))
    assert await labeler.label(_audio()) is None
    assert await labeler.label(_audio()) is None
    assert await labeler.label(_audio()) == "Собеседник 2"
    assert await labeler.label(_audio()) == "Собеседник 1"


async def test_short_phrase_stays_without_a_label() -> None:
    embedder = _Embedder([ANNA])
    assert await SpeakerLabeler(CFG, embedder).label(_audio(0.1)) is None
    assert embedder.voices == [ANNA], "короткая фраза не должна портить отпечатки"


@pytest.mark.parametrize("failure", [STTUnavailable("нет"), GenerationFailed("сбой")])
async def test_failure_leaves_the_phrase_without_a_label(failure: Exception) -> None:
    assert await SpeakerLabeler(CFG, _Embedder(failure=failure)).label(_audio()) is None


def test_label_goes_before_the_text() -> None:
    assert labelled("Привет", "Собеседник 2") == "Собеседник 2: Привет"
    assert labelled("Привет", None) == "Привет"


@dataclass(slots=True)
class _Events:
    finals: list[str] = field(default_factory=list)

    async def barge_in(self) -> None:
        """Не нужен в этих тестах."""

    async def hypothesis(self, text: str) -> None:
        """Не нужен в этих тестах."""

    async def final(self, text: str, ended_ns: int) -> None:
        del ended_ns
        self.finals.append(text)


async def _settle() -> None:
    for _ in range(2000):
        await asyncio.sleep(0)


async def _say(embedder: _Embedder, phrases: int) -> list[str]:
    events = _Events()
    cfg = VoiceConfig(interim_ms=60_000, min_phrase_ms=200, segmenter=SEGMENTS)
    listener = VoiceListener(FakeVad(), FakeSTT("Привет"), events, cfg)
    listener.speakers = SpeakerLabeler(CFG, embedder)
    loop = asyncio.create_task(listener.run())
    for _ in range(phrases):
        listener.feed(_audio(0.6))
        listener.feed(_audio(0.5, loud=False))
        await asyncio.sleep(0.1)
        await _settle()
    loop.cancel()
    await asyncio.wait([loop])
    return events.finals


async def test_listener_labels_phrases_once_a_second_voice_appears() -> None:
    assert await _say(_Embedder([ANNA, BORIS, ANNA]), 3) == [
        "Привет",
        "Собеседник 2: Привет",
        "Собеседник 1: Привет",
    ]


async def test_slow_embedder_does_not_hold_the_reply() -> None:
    finals = await _say(_Embedder([ANNA], delay_s=5.0), 1)
    assert finals == ["Привет"]


async def test_name_is_found_after_the_label() -> None:
    events = _Events()
    bridge = AddressedEvents(events, ("мика",))
    await bridge.final("Собеседник 2: Мика, привет", 0)
    await bridge.final("Собеседник 2: передай соль", 0)
    assert events.finals == ["Собеседник 2: привет"]  # имя из запроса вырезается


async def test_missing_model_is_unavailable(tmp_path: Path) -> None:
    embedder = SherpaSpeakerEmbedder(
        SpeakerModelConfig(model_path=tmp_path / "нет.onnx", threads=1)
    )
    with pytest.raises(STTUnavailable, match="Нет модели"):
        await embedder.embed(_audio())


def test_report_finds_mistakes() -> None:
    heard = [Heard("анна", 1), Heard("анна", 1), Heard("борис", 2), Heard("борис", 1)]
    assert error_rate(heard) == pytest.approx(0.25)
    assert "ошибок: 25 %" in render(heard)
    assert person_of(Path("01_Anna.wav")) == "anna"
    assert person_of(Path("заметка.wav")) is None


@pytest.mark.slow
@pytest.mark.skipif(not MODEL.is_file(), reason="нет модели голоса")
async def test_real_model_gives_a_fixed_size_print() -> None:
    embedder = SherpaSpeakerEmbedder(SpeakerModelConfig(model_path=MODEL, threads=2))
    first = await embedder.embed(_audio(1.5))
    second = await embedder.embed(_audio(2.5))
    assert len(first) == len(second) > 0
