"""Загрузка персоны из `personas/*.toml` в доменную `Persona` с понятными ошибками (FR-11)."""

import tomllib
from itertools import chain
from pathlib import Path

from pydantic import Field, ValidationError

from vtuber.domain import ConfigError, Message, Persona, Role
from vtuber.kernel import ConfigSection


class PersonaConfig(ConfigSection):
    """Секция `[persona]`: путь к файлу персоны относительно корня проекта."""

    file: Path


_INITIATIVE = (
    "(Ведущий давно молчит. Заведи разговор сама: коротко спроси о чём-нибудь или продолжи прошлую "
    "тему. Об этой просьбе не упоминай.)"
)


class _Example(ConfigSection):
    user: str
    assistant: str


class _PersonaFile(ConfigSection):
    name: str
    language: str
    description: str
    speech_style: str
    rules: list[str] = Field(min_length=1)
    examples: list[_Example] = Field(default_factory=list)
    initiative: str = _INITIATIVE


def load_persona(path: Path) -> Persona:
    """Читает и проверяет файл персоны; лишний или пропущенный ключ — ошибка.

    Raises:
        ConfigError: файла нет, он не TOML или не проходит проверку — с путём к файлу.

    """
    name = path.as_posix()
    try:
        with path.open("rb") as file:
            raw = _PersonaFile.model_validate(tomllib.load(file))
    except FileNotFoundError as exc:
        msg = f"Не найден файл персоны {name} — проверьте [persona].file в config"
        raise ConfigError(msg) from exc
    except (tomllib.TOMLDecodeError, ValidationError) as exc:
        msg = f"Ошибка в файле персоны {name}: {exc} — исправьте файл"
        raise ConfigError(msg) from exc
    examples = chain.from_iterable(_as_messages(example) for example in raw.examples)
    return Persona(
        name=raw.name,
        language=raw.language,
        description=raw.description,
        speech_style=raw.speech_style,
        rules=tuple(raw.rules),
        examples=tuple(examples),
        initiative=raw.initiative,
    )


def _as_messages(example: _Example) -> tuple[Message, Message]:
    return Message(Role.USER, example.user), Message(Role.ASSISTANT, example.assistant)
