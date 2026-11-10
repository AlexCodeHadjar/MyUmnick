"""Издание (Этап 20, ADR-0032): файлы конфига и ключи общего `user.toml`, которые не действуют."""

import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from pydantic import Field

from vtuber.application.language import EN_PACK, RU_PACK, LanguagePack
from vtuber.application.prompting import with_profile
from vtuber.bootstrap.persona import load_persona
from vtuber.domain import ConfigError, ContentProfile, EditionId, Persona
from vtuber.kernel import ConfigFiles, ConfigSection, get_logger

EDITION_ENV: Final = "VTUBER_EDITION__ID"
_log = get_logger(__name__)
# Ключи, которые зависят от языка издания: в общем `user.toml` они действуют только для `ru`
# (прежний файл пользователя), иначе русская персона и голос попали бы в английское издание.
LANGUAGE_BOUND_KEYS: Final = frozenset(
    {
        "persona",
        "tts",
        "context.chars_per_token",
        "pipeline.filler",
        "stt.whisper.language",
        "stt.addressing",
        "memory.store_path",
        "memory.vault_path",
        "memory.inbox",
        "memory.transfer_to",
        "llama_server.model",
        "setup.choice_file",
        "setup.catalog_file",
    }
)


class EditionConfig(ConfigSection):
    """Секция `[edition]`: задаётся файлом `config/editions/<id>.toml`, а не пользователем."""

    id: EditionId
    language: str = Field(min_length=2)
    content_profile: ContentProfile
    stream_safe: bool


def resolve_edition(arg: str | None, env: Mapping[str, str]) -> EditionId:
    """Издание из `--edition`, иначе из `VTUBER_EDITION__ID`, иначе `ru` (прежнее поведение).

    Raises:
        ConfigError: неизвестное издание — со списком доступных.

    """
    upper = {key.upper(): value for key, value in env.items()}
    value = (arg or upper.get(EDITION_ENV) or EditionId.RU).strip().lower()
    try:
        return EditionId(value)
    except ValueError as exc:
        known = ", ".join(edition.value for edition in EditionId)
        msg = f"Неизвестное издание {value!r}; доступны: {known}"
        raise ConfigError(msg) from exc


def edition_files(config_dir: Path, edition: EditionId) -> ConfigFiles:
    """Файлы издания; у `ru` мастер пишет прежний `setup.toml` и действуют все ключи `user.toml`."""
    russian = edition is EditionId.RU
    return ConfigFiles(
        default=config_dir / "default.toml",
        user=config_dir / "user.toml",
        generated=config_dir / ("setup.toml" if russian else f"setup.{edition}.toml"),
        edition=config_dir / "editions" / f"{edition}.toml",
        edition_user=config_dir / f"user.{edition}.toml",
        user_ignored=frozenset() if russian else LANGUAGE_BOUND_KEYS,
    )


def check_edition(loaded: EditionConfig, expected: EditionId) -> None:
    """Файл издания или переменная окружения не должны подменить выбранное издание.

    Raises:
        ConfigError: `[edition].id` не совпадает с выбранным изданием.

    """
    if loaded.id is not expected:
        msg = (
            f"[edition].id = {loaded.id} не совпадает с выбранным изданием {expected}: "
            f"проверьте config/editions/{expected}.toml и {EDITION_ENV}"
        )
        raise ConfigError(msg)


def ignored_user_keys(files: ConfigFiles) -> list[str]:
    """Языковые ключи общего `user.toml`, которые в этом издании не действуют (предупреждение)."""
    if not files.user_ignored or not files.user.is_file():
        return []
    try:
        with files.user.open("rb") as file:
            tree: object = tomllib.load(file)
    except tomllib.TOMLDecodeError:
        return []  # ошибку синтаксиса уже назвал загрузчик конфига
    return sorted(key for key in files.user_ignored if _has(tree, key.split(".")))


def _has(tree: object, path: list[str]) -> bool:
    node = tree
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return False
        node = node[key]
    return True


def language_pack(language: str) -> LanguagePack:
    """Языковой пакет по `[edition].language`.

    Raises:
        ConfigError: для языка нет пакета — со списком доступных.

    """
    packs = {pack.language: pack for pack in (RU_PACK, EN_PACK)}
    try:
        return packs[language]
    except KeyError as exc:
        msg = (
            f"[edition].language = {language!r}: нет языкового пакета; доступны: {', '.join(packs)}"
        )
        raise ConfigError(msg) from exc


def edition_persona(path: Path, edition: EditionConfig) -> Persona:
    """Персона из файла с правилами профиля содержания издания (ADR-0033).

    Raises:
        ConfigError: файл персоны неверен; для языка нет пакета.

    """
    texts = language_pack(edition.language).prompt.profile
    persona = load_persona(path)
    return with_profile(persona, texts, edition.content_profile, stream_safe=edition.stream_safe)


def warn_ignored_user_keys(config_dir: Path, edition: EditionId) -> None:
    """Предупреждение: ключи общего `user.toml` (он для `ru`) здесь не действуют."""
    keys = ignored_user_keys(edition_files(config_dir, edition))
    if keys:
        _log.warning("config.user_keys_ignored", keys=keys)
