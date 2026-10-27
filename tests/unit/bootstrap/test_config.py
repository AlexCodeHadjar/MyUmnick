from pathlib import Path

from vtuber.bootstrap import AppConfig, load_app_config
from vtuber.kernel import ConfigFiles, load_config

ROOT = Path(__file__).resolve().parents[3]


def test_repository_default_config_is_valid(tmp_path: Path) -> None:
    files = ConfigFiles(default=ROOT / "config" / "default.toml", user=tmp_path / "absent.toml")

    cfg = load_config(AppConfig, files, env={})

    assert cfg.logging.level == "INFO"
    assert cfg.llm.base_url == "http://127.0.0.1:8080"


def test_env_reaches_section_of_app_config() -> None:
    cfg = load_app_config(ROOT, env={"VTUBER_LOGGING__LEVEL": "DEBUG"})

    assert cfg.logging.level == "DEBUG"
