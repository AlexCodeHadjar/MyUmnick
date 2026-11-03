"""Сборка мастера первого запуска (S-13.2) и запись выбора пользователя в `config/setup.toml`."""

import json
import shutil
import tomllib
from collections.abc import Mapping
from pathlib import Path

from pydantic import ValidationError

from vtuber.adapters.setup import HttpFetcher, HttpFetcherConfig
from vtuber.application.setup import Installer, SetupCatalog, SetupWizard
from vtuber.domain import ConfigError
from vtuber.kernel import ConfigSection
from vtuber.ports import GpuProbe


class SetupConfig(ConfigSection):
    """Секция `[setup]`: мастер включён только в поставке; при разработке модели кладут сами."""

    enabled: bool
    install_dir: Path
    catalog_file: Path
    choice_file: Path
    http: HttpFetcherConfig

    def resolved(self, root: Path) -> "SetupConfig":
        """Копия с путями от корня проекта."""
        return self.model_copy(
            update={
                "install_dir": root / self.install_dir,
                "catalog_file": root / self.catalog_file,
                "choice_file": root / self.choice_file,
            }
        )


def load_catalog(path: Path) -> SetupCatalog:
    """Каталог компонентов.

    Raises:
        ConfigError: файла нет или он не проходит проверку.

    """
    try:
        with path.open("rb") as file:
            return SetupCatalog.model_validate(tomllib.load(file))
    except (OSError, tomllib.TOMLDecodeError, ValidationError) as exc:
        msg = f"Каталог компонентов {path} не читается: {exc} — переустановите приложение"
        raise ConfigError(msg) from exc


def render_choice(sections: Mapping[str, Mapping[str, str | bool]]) -> str:
    """TOML-файл из секций; строки в JSON совпадают со строками TOML, нужных нам значений хватит."""
    lines: list[str] = ["# Записано мастером первого запуска. Свои настройки — в user.toml."]
    for section, values in sections.items():
        lines += ["", f"[{section}]"]
        lines += [
            f"{key} = {json.dumps(value, ensure_ascii=False)}" for key, value in values.items()
        ]
    return "\n".join(lines) + "\n"


def write_choice(path: Path, sections: Mapping[str, Mapping[str, str | bool]]) -> None:
    """Заменяет файл целиком и атомарно: сбой на середине не оставит битый конфиг."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(render_choice(sections), encoding="utf-8", newline="\n")
    temporary.replace(path)


def build_wizard(cfg: SetupConfig, probe: GpuProbe) -> SetupWizard:
    """Мастер на настоящей сети и диске."""
    installer = Installer(
        cfg.install_dir, HttpFetcher(cfg.http), lambda path: shutil.disk_usage(path).free
    )
    catalog = load_catalog(cfg.catalog_file)
    return SetupWizard(
        catalog, installer, probe, lambda sections: write_choice(cfg.choice_file, sections)
    )
