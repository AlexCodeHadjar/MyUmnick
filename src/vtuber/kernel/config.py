"""Загрузка конфигурации: default.toml < user.toml < переменные VTUBER_*, проверка pydantic."""

import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, ValidationError
from pydantic_core import ErrorDetails

from vtuber.domain import ConfigError

ENV_PREFIX: Final = "VTUBER_"
ENV_NESTING: Final = "__"
ENV_SOURCE: Final = "переменные окружения VTUBER_*"

type ConfigTree = dict[str, object]


class ConfigSection(BaseModel):
    """База секции конфига: неизменяема, лишний ключ — ошибка (опечатка не пройдёт молча).

    Секцию описывает модуль, которому она нужна; значений по умолчанию в коде нет —
    единственный источник умолчаний `config/default.toml`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")


@dataclass(frozen=True, slots=True)
class ConfigFiles:
    """Файлы конфигурации: `default` обязателен, остальные — если есть.

    `generated` пишет мастер первого запуска: он не должен трогать правки пользователя в `user`.
    """

    default: Path
    user: Path
    generated: Path | None = None


@dataclass(frozen=True, slots=True)
class _Source:
    name: str
    tree: ConfigTree


def load_config[T: ConfigSection](model: type[T], files: ConfigFiles, env: Mapping[str, str]) -> T:
    """Собирает конфиг из файлов и окружения и проверяет его моделью `model`.

    Приоритет: env > user > generated > default. `VTUBER_<СЕКЦИЯ>__<ПОЛЕ>` задаёт поле секции.

    Raises:
        ConfigError: файл не найден или не разбирается как TOML; значение не проходит проверку —
            сообщение называет поле, полученное значение и источник, где его исправить.

    """
    sources = [_read(files.default)]
    if files.generated is not None and files.generated.is_file():
        sources.append(_read(files.generated))
    if files.user.is_file():
        sources.append(_read(files.user))
    sources.append(_Source(ENV_SOURCE, _env_tree(env)))
    merged = _merge_all(source.tree for source in sources)
    try:
        return model.model_validate(merged)
    except ValidationError as exc:
        raise ConfigError(_describe(exc, sources)) from exc


def _read(path: Path) -> _Source:
    name = path.as_posix()
    try:
        with path.open("rb") as file:
            return _Source(name, tomllib.load(file))
    except FileNotFoundError as exc:
        msg = f"Не найден файл конфигурации {name} — восстановите его из репозитория"
        raise ConfigError(msg) from exc
    except tomllib.TOMLDecodeError as exc:
        msg = f"Ошибка синтаксиса TOML в {name}: {exc} — исправьте файл"
        raise ConfigError(msg) from exc


def _env_tree(env: Mapping[str, str]) -> ConfigTree:
    paths = (
        (key[len(ENV_PREFIX) :].lower().split(ENV_NESTING), value)
        for key, value in env.items()
        if key.upper().startswith(ENV_PREFIX)
    )
    return _merge_all(_nest(path, value) for path, value in paths)


def _nest(path: list[str], value: str) -> ConfigTree:
    tree: ConfigTree = {path[-1]: value}
    for key in reversed(path[:-1]):
        tree = {key: tree}
    return tree


def _merge_all(trees: Iterable[ConfigTree]) -> ConfigTree:
    merged: ConfigTree = {}
    for tree in trees:
        merged = _merge(merged, tree)
    return merged


def _merge(base: ConfigTree, override: ConfigTree) -> ConfigTree:
    merged = dict(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _merge(current, value)
        else:
            merged[key] = value
    return merged


def _describe(error: ValidationError, sources: Sequence[_Source]) -> str:
    lines = [f"Конфигурация не прошла проверку ({error.error_count()}):"]
    lines += [f"  {_describe_item(item, sources)}" for item in error.errors()]
    return "\n".join(lines)


def _describe_item(item: ErrorDetails, sources: Sequence[_Source]) -> str:
    path = tuple(str(part) for part in item["loc"])
    field = ".".join(path)
    if item["type"] == "missing":
        return f"{field}: поле обязательно, но не задано — добавьте его в {sources[0].name}"
    holders = [source.name for source in sources if _contains(source.tree, path)]
    origin = holders[-1] if holders else "—"
    return f"{field}: {item['msg']}; получено {item['input']!r} — исправьте в {origin}"


def _contains(tree: object, path: Sequence[str]) -> bool:
    node = tree
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return False
        node = node[key]
    return True
