"""Порт выбора навыков (Этап 23, ADR-0043): какие навыки пользователь включил или выключил."""

from collections.abc import Mapping
from typing import Protocol


class SkillChoicesPort(Protocol):
    """Выбор пользователя поверх конфига: id навыка → включён. Ошибки диска — `ConfigError`."""

    async def load(self) -> dict[str, bool]:
        """Сохранённый выбор; нет файла или он битый — пусто (всё как в конфиге)."""
        ...

    async def save(self, choices: Mapping[str, bool]) -> None:
        """Записать выбор целиком (атомарно)."""
        ...
