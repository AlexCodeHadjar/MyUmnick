from pathlib import Path

import pytest

from vtuber.adapters.tts import PiperTTS, SileroTTS
from vtuber.bootstrap import load_app_config, tts_backends
from vtuber.domain import ConfigError

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ("backend", "expected"), [("silero", SileroTTS), ("piper", PiperTTS), ("none", type(None))]
)
def test_tts_backend_is_chosen_by_config_name(backend: str, expected: type) -> None:
    cfg = load_app_config(ROOT, {}).tts

    assert isinstance(tts_backends().create(backend, cfg), expected)


def test_unknown_tts_backend_is_a_config_error() -> None:
    with pytest.raises(ConfigError, match="tts"):
        tts_backends().create("espeak", load_app_config(ROOT, {}).tts)


def test_model_paths_are_resolved_from_project_root(tmp_path: Path) -> None:
    cfg = load_app_config(ROOT, {}).tts.resolved(tmp_path)

    assert cfg.silero.model_path == tmp_path / "models/tts/silero/v5_6_ru.pt"
    assert cfg.piper.model_path.parent == tmp_path / "models/tts/piper"


def test_default_config_reads_voice_and_chunker_sections() -> None:
    cfg = load_app_config(ROOT, {"VTUBER_TTS__BACKEND": "none"})

    assert cfg.tts.backend == "none"
    assert cfg.pipeline.chunker.first_min_words == 4
    assert cfg.tts.silero.sample_rate == 48000
