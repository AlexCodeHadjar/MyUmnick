"""Слои издания (Этап 20, ADR-0032): default < edition < generated < user < edition_user < env."""

from dataclasses import replace
from pathlib import Path

import pytest

from vtuber.domain import ConfigError
from vtuber.kernel import ConfigFiles, ConfigSection, load_config


class _Persona(ConfigSection):
    file: str


class _Voice(ConfigSection):
    backend: str
    rate: int


class _App(ConfigSection):
    persona: _Persona
    voice: _Voice


DEFAULT = """
[persona]
file = "ru.toml"

[voice]
backend = "silero"
rate = 48000
"""


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _files(tmp_path: Path) -> ConfigFiles:
    return ConfigFiles(
        default=_write(tmp_path / "default.toml", DEFAULT),
        user=tmp_path / "user.toml",
        generated=tmp_path / "setup.en.toml",
        edition=_write(tmp_path / "en.toml", '[persona]\nfile = "en.toml"\n'),
        edition_user=tmp_path / "user.en.toml",
    )


def test_edition_file_overrides_default(tmp_path: Path) -> None:
    cfg = load_config(_App, _files(tmp_path), env={})

    assert cfg.persona.file == "en.toml"
    assert cfg.voice.backend == "silero"


def test_order_of_all_layers(tmp_path: Path) -> None:
    files = _files(tmp_path)
    _write(tmp_path / "setup.en.toml", '[voice]\nbackend = "piper"\nrate = 22050\n')
    _write(tmp_path / "user.toml", "[voice]\nrate = 24000\n")
    _write(tmp_path / "user.en.toml", '[voice]\nbackend = "kokoro"\n')

    cfg = load_config(_App, files, env={"VTUBER_VOICE__RATE": "16000"})

    assert cfg.voice.backend == "kokoro"  # user издания сильнее мастера
    assert cfg.voice.rate == 16000  # env сильнее всех файлов


def test_ignored_keys_of_shared_user_file_do_not_apply(tmp_path: Path) -> None:
    files = replace(_files(tmp_path), user_ignored=frozenset({"persona", "voice.backend"}))
    shared = '[persona]\nfile = "mika_long.toml"\n[voice]\nbackend = "x"\nrate = 1\n'
    _write(tmp_path / "user.toml", shared)

    cfg = load_config(_App, files, env={})

    assert cfg.persona.file == "en.toml"
    assert cfg.voice.backend == "silero"
    assert cfg.voice.rate == 1  # не языковой ключ общего файла действует


def test_ignored_keys_still_apply_from_edition_user_file(tmp_path: Path) -> None:
    files = replace(_files(tmp_path), user_ignored=frozenset({"persona"}))
    _write(tmp_path / "user.en.toml", '[persona]\nfile = "mine.toml"\n')

    assert load_config(_App, files, env={}).persona.file == "mine.toml"


def test_missing_edition_file_is_an_error(tmp_path: Path) -> None:
    files = replace(_files(tmp_path), edition=tmp_path / "xx.toml")

    with pytest.raises(ConfigError, match=r"xx\.toml"):
        load_config(_App, files, env={})


def test_wrong_value_in_edition_file_names_it(tmp_path: Path) -> None:
    files = _files(tmp_path)
    _write(tmp_path / "en.toml", '[voice]\nrate = "fast"\n')

    with pytest.raises(ConfigError, match=r"voice\.rate.*en\.toml"):
        load_config(_App, files, env={})
