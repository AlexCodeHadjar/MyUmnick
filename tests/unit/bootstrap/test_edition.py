"""Издание при загрузке конфига (S-20.1, ADR-0032)."""

import shutil
import tomllib
from pathlib import Path

import pytest

from vtuber.bootstrap import load_app_config
from vtuber.bootstrap.edition import (
    LANGUAGE_BOUND_KEYS,
    edition_files,
    ignored_user_keys,
    resolve_edition,
)
from vtuber.domain import ConfigError, ContentProfile, EditionId

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """Корень с конфигом из репозитория, но без личных файлов разработчика."""
    config = tmp_path / "config"
    shutil.copytree(ROOT / "config" / "editions", config / "editions")
    shutil.copy(ROOT / "config" / "default.toml", config / "default.toml")
    return tmp_path


def _user(root: Path, name: str, text: str) -> None:
    (root / "config" / name).write_text(text, encoding="utf-8")


def test_without_edition_config_is_russian_as_before(root: Path) -> None:
    cfg = load_app_config(root, {})

    assert cfg.edition.id is EditionId.RU
    assert cfg.edition.content_profile is ContentProfile.STANDARD
    assert cfg.memory.store_path == Path("data/memory.sqlite")
    assert cfg.stt.whisper.language == "ru"


def test_english_edition_has_its_own_data_and_language(root: Path) -> None:
    cfg = load_app_config(root, {}, EditionId.EN)

    assert cfg.edition.content_profile is ContentProfile.UNFILTERED
    assert cfg.edition.stream_safe is False
    assert cfg.memory.store_path == Path("data/en/memory.sqlite")
    assert cfg.memory.vault_path == Path("data/en/vault")
    assert cfg.stt.whisper.language == "en"
    assert cfg.setup.choice_file == Path("config/setup.en.toml")
    assert cfg.tts.backend == "piper"
    assert cfg.tts.piper.model_path == Path("models/tts/piper/en_US-ljspeech-high.onnx")


def test_wizard_file_of_edition_is_the_one_it_writes(root: Path) -> None:
    for edition in EditionId:
        files = edition_files(root / "config", edition)
        cfg = load_app_config(root, {}, edition)

        assert files.generated == root / cfg.setup.choice_file


def test_russian_user_file_does_not_leak_into_english(root: Path) -> None:
    _user(
        root, "user.toml", '[persona]\nfile = "personas/mika_long.toml"\n[tts]\nbackend = "none"\n'
    )

    ru = load_app_config(root, {})
    en = load_app_config(root, {}, EditionId.EN)

    assert ru.persona.file == Path("personas/mika_long.toml")
    assert en.persona.file == Path("personas/en/default.toml")
    assert en.tts.backend != "none"


def test_edition_user_file_applies_only_to_its_edition(root: Path) -> None:
    _user(root, "user.en.toml", '[logging]\nlevel = "DEBUG"\n')

    assert load_app_config(root, {}, EditionId.EN).logging.level == "DEBUG"
    assert load_app_config(root, {}).logging.level == "INFO"


def test_ignored_keys_are_reported_only_outside_russian(root: Path) -> None:
    _user(root, "user.toml", '[persona]\nfile = "x.toml"\n[logging]\nlevel = "DEBUG"\n')
    config = root / "config"

    assert ignored_user_keys(edition_files(config, EditionId.RU)) == []
    assert ignored_user_keys(edition_files(config, EditionId.EN)) == ["persona"]


def test_edition_cannot_be_swapped_by_environment(root: Path) -> None:
    with pytest.raises(ConfigError, match=r"\[edition\]\.id"):
        load_app_config(root, {"VTUBER_EDITION__ID": "en"}, EditionId.RU)


@pytest.mark.parametrize(
    ("arg", "env", "expected"),
    [
        (None, {}, EditionId.RU),
        ("en", {}, EditionId.EN),
        (None, {"vtuber_edition__id": "EN"}, EditionId.EN),
        ("ru", {"VTUBER_EDITION__ID": "en"}, EditionId.RU),
    ],
)
def test_resolve_edition(arg: str | None, env: dict[str, str], expected: EditionId) -> None:
    assert resolve_edition(arg, env) is expected


def test_unknown_edition_lists_known_ones() -> None:
    with pytest.raises(ConfigError, match="ru, en"):
        resolve_edition("de", {})


def test_language_bound_keys_exist_in_default_config(root: Path) -> None:
    tree = tomllib.loads((root / "config" / "default.toml").read_text(encoding="utf-8"))
    for key in LANGUAGE_BOUND_KEYS:
        node: object = tree
        for part in key.split("."):
            assert isinstance(node, dict)
            assert part in node, key
            node = node[part]
