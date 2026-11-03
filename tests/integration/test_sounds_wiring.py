"""Подключение звуков вокруг: по умолчанию выключены, без модели голос работает (S-14.4)."""

from pathlib import Path

from tests.fakes import FakeClock, FakeSTT, FakeVad
from vtuber.application.voice import VoiceConfig, VoiceListener
from vtuber.bootstrap import load_app_config
from vtuber.bootstrap.container import Core
from vtuber.bootstrap.voice_input import _LazyVoice
from vtuber.kernel import EventBus, Telemetry

ROOT = Path(__file__).resolve().parents[2]


class _Events:
    async def barge_in(self) -> None:
        """Не нужен в этих тестах."""

    async def hypothesis(self, text: str) -> None:
        """Не нужен в этих тестах."""

    async def final(self, text: str, ended_ns: int) -> None:
        """Не нужен в этих тестах."""


def test_sounds_are_off_by_default() -> None:
    assert load_app_config(ROOT, {}).stt.sounds.enabled is False


def test_voice_config_keeps_working_without_the_hold() -> None:
    cfg = load_app_config(ROOT, {}).stt.voice
    assert isinstance(cfg, VoiceConfig)
    assert cfg.unfinished_hold_ms > 0


async def test_missing_model_leaves_voice_input_alone(tmp_path: Path) -> None:
    stt = load_app_config(ROOT, {}).stt
    missing = stt.sound_model.model_copy(update={"model_path": tmp_path / "нет.onnx"})
    cfg = stt.model_copy(update={"sound_model": missing})
    bus = EventBus()
    core = Core(bus, Telemetry(bus, FakeClock()))
    voice = _LazyVoice(cfg, _Events(), core, 1.0)
    listener = VoiceListener(FakeVad(), FakeSTT(), _Events(), cfg.voice)

    await voice.watch_sounds(listener)  # без модели задача заканчивается сама и без ошибки
