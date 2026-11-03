"""SenseVoice: контракт `SoundClassifierPort` и разбор меток (S-14.4); модель — если она есть."""

import array
from pathlib import Path

import pytest

from tools.eval_sounds import Window, label_of, render
from vtuber.adapters.stt.sensevoice import SenseVoiceConfig, SenseVoiceSounds, sound_of
from vtuber.domain import AudioChunk, AudioFormat, SoundKind, STTUnavailable

MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "stt" / "sensevoice"
MODEL = MODEL_DIR / "model.int8.onnx"
RATE = AudioFormat(16_000)


def _cfg(model: Path = MODEL) -> SenseVoiceConfig:
    return SenseVoiceConfig(
        model_path=model, tokens_path=MODEL_DIR / "tokens.txt", threads=2, timeout_s=30.0
    )


@pytest.mark.parametrize(
    ("tag", "kind"),
    [
        ("<|Laughter|>", SoundKind.LAUGHTER),
        ("<|BGM|>", SoundKind.MUSIC),
        ("<|Speech|>", None),
        ("<|Breath|>", None),
        ("<|Event_UNK|>", None),
        ("", None),
        ("<|Новое|>", None),
    ],
)
def test_tags_become_sounds(tag: str, kind: SoundKind | None) -> None:
    assert sound_of(tag) is kind


async def test_not_loaded_model_is_unavailable() -> None:
    chunk = AudioChunk(RATE, b"\0\0" * 100)
    with pytest.raises(STTUnavailable):
        await SenseVoiceSounds(_cfg()).classify(chunk)


async def test_missing_file_is_unavailable(tmp_path: Path) -> None:
    with pytest.raises(STTUnavailable, match="Нет модели"):
        async with SenseVoiceSounds(_cfg(tmp_path / "нет.onnx")):
            pass


@pytest.mark.slow
@pytest.mark.skipif(not MODEL.is_file(), reason="нет модели SenseVoice")
async def test_real_model_answers_with_a_sound_or_nothing() -> None:
    tone = array.array("h", [8000 if i % 40 < 20 else -8000 for i in range(RATE.sample_rate)])
    async with SenseVoiceSounds(_cfg()) as sounds:
        kind = await sounds.classify(AudioChunk(RATE, tone.tobytes()))
    assert kind is None or isinstance(kind, SoundKind)


@pytest.mark.parametrize(
    ("name", "label"),
    [
        ("laughter_1.wav", "laughter"),
        ("Cough-kitchen.wav", "cough"),
        ("speech_ru.wav", "none"),
        ("note.wav", None),
    ],
)
def test_label_comes_from_the_file_name(name: str, label: str | None) -> None:
    assert label_of(Path(name)) == label


def test_report_counts_hits_and_false_alarms() -> None:
    report = render(
        [
            Window("laughter", "laughter", 0.2),
            Window("laughter", "none", 0.2),
            Window("none", "music", 0.2),
        ]
    )
    assert "laughter: 1/2 (50 %)" in report
    assert "none: 0/1" in report
    assert "'music': 1" in report
