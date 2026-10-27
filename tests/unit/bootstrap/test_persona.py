from pathlib import Path

import pytest

from vtuber.bootstrap import load_persona
from vtuber.domain import ConfigError, Message, Role

ROOT = Path(__file__).resolve().parents[3]
VALID = """
name = "Мика"
language = "русский"
description = "Ведущая."
speech_style = "Коротко."
rules = ["Отвечай коротко."]

[[examples]]
user = "Привет!"
assistant = "<happy>Привет-привет!"
"""


def test_repository_default_persona_loads() -> None:
    persona = load_persona(ROOT / "personas" / "default.toml")

    assert persona.name
    assert any("{emotions}" in rule for rule in persona.rules)


def test_examples_become_user_assistant_pairs(tmp_path: Path) -> None:
    path = tmp_path / "persona.toml"
    path.write_text(VALID, encoding="utf-8")

    persona = load_persona(path)

    assert persona.rules == ("Отвечай коротко.",)
    assert persona.examples == (
        Message(Role.USER, "Привет!"),
        Message(Role.ASSISTANT, "<happy>Привет-привет!"),
    )


@pytest.mark.parametrize(
    "text",
    [
        VALID.replace('name = "Мика"\n', ""),
        VALID + 'mood = "весёлая"\n',
        VALID.replace('rules = ["Отвечай коротко."]', "rules = []"),
        "name = [не toml",
    ],
)
def test_bad_persona_file_is_config_error_naming_the_file(tmp_path: Path, text: str) -> None:
    path = tmp_path / "broken.toml"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ConfigError, match=r"broken\.toml"):
        load_persona(path)


def test_missing_persona_file_is_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match=r"nope\.toml"):
        load_persona(tmp_path / "nope.toml")
