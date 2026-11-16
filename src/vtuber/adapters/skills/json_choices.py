"""Выбор навыков в JSON (`data/skills.json`, у английского издания — свой файл)."""

import asyncio
import json
from collections.abc import Mapping
from pathlib import Path

from vtuber.domain import ConfigError


class JsonSkillChoices:
    """Реализует `SkillChoicesPort`; запись — через временный файл, сбой не оставит битый выбор."""

    def __init__(self, path: Path) -> None:
        self._path = path

    async def load(self) -> dict[str, bool]:
        """Выбор с диска; нет файла или он битый — пусто."""
        return await asyncio.to_thread(self._load)

    async def save(self, choices: Mapping[str, bool]) -> None:
        """Записать выбор."""
        try:
            await asyncio.to_thread(self._save, dict(choices))
        except OSError as exc:
            msg = f"Выбор навыков {self._path} не записывается: {exc}"
            raise ConfigError(msg) from exc

    def _load(self) -> dict[str, bool]:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        if not isinstance(raw, dict):
            return {}
        return {str(key): value for key, value in raw.items() if isinstance(value, bool)}

    def _save(self, choices: dict[str, bool]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".tmp")
        temporary.write_text(json.dumps(choices, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self._path)
