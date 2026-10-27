from pathlib import Path
from typing import Literal

import pytest
from pydantic import ValidationError

from vtuber.domain import ConfigError
from vtuber.kernel import ConfigFiles, ConfigSection, load_config


class _Server(ConfigSection):
    host: str
    port: int


class _Logs(ConfigSection):
    level: Literal["DEBUG", "INFO"]


class _App(ConfigSection):
    server: _Server
    logs: _Logs


DEFAULT = """
[server]
host = "127.0.0.1"
port = 8765

[logs]
level = "INFO"
"""


def _files(tmp_path: Path, default: str = DEFAULT, user: str | None = None) -> ConfigFiles:
    files = ConfigFiles(default=tmp_path / "default.toml", user=tmp_path / "user.toml")
    files.default.write_text(default, encoding="utf-8")
    if user is not None:
        files.user.write_text(user, encoding="utf-8")
    return files


def test_default_file_alone_is_enough(tmp_path: Path) -> None:
    cfg = load_config(_App, _files(tmp_path), env={})

    assert cfg.server.port == 8765
    assert cfg.logs.level == "INFO"


def test_user_file_overrides_only_its_keys(tmp_path: Path) -> None:
    cfg = load_config(_App, _files(tmp_path, user="[server]\nport = 9000\n"), env={})

    assert cfg.server.port == 9000
    assert cfg.server.host == "127.0.0.1"


def test_env_overrides_user_and_default(tmp_path: Path) -> None:
    files = _files(tmp_path, user="[server]\nport = 9000\n")

    cfg = load_config(_App, files, env={"VTUBER_SERVER__PORT": "9100", "OTHER": "x"})

    assert cfg.server.port == 9100


def test_env_names_are_case_insensitive(tmp_path: Path) -> None:
    cfg = load_config(_App, _files(tmp_path), env={"vtuber_logs__LEVEL": "DEBUG"})

    assert cfg.logs.level == "DEBUG"


def test_wrong_type_in_user_file_names_file_field_and_value(tmp_path: Path) -> None:
    files = _files(tmp_path, user='[server]\nport = "восемь"\n')

    with pytest.raises(ConfigError) as error:
        load_config(_App, files, env={})

    message = str(error.value)
    assert "server.port" in message
    assert "user.toml" in message
    assert "'восемь'" in message
    assert "integer" in message
    assert isinstance(error.value.__cause__, ValidationError)


def test_wrong_value_from_env_names_env_as_source(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match=r"logs\.level.*VTUBER_"):
        load_config(_App, _files(tmp_path), env={"VTUBER_LOGS__LEVEL": "LOUD"})


def test_unknown_key_is_rejected_with_its_source(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match=r"server\.prot.*user\.toml"):
        load_config(_App, _files(tmp_path, user="[server]\nprot = 1\n"), env={})


def test_missing_field_points_to_default_file(tmp_path: Path) -> None:
    files = _files(tmp_path, default='[server]\nhost = "h"\n[logs]\nlevel = "INFO"\n')

    with pytest.raises(ConfigError, match=r"server\.port.*default\.toml"):
        load_config(_App, files, env={})


def test_toml_syntax_error_names_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match=r"user\.toml"):
        load_config(_App, _files(tmp_path, user="[server\n"), env={})


def test_missing_default_file_is_an_error(tmp_path: Path) -> None:
    files = ConfigFiles(default=tmp_path / "nope.toml", user=tmp_path / "user.toml")

    with pytest.raises(ConfigError, match=r"nope\.toml"):
        load_config(_App, files, env={})


def test_loaded_config_is_immutable(tmp_path: Path) -> None:
    cfg = load_config(_App, _files(tmp_path), env={})

    with pytest.raises(ValidationError):
        cfg.server.port = 1  # type: ignore[misc]  # проверяем запрет и во время выполнения
