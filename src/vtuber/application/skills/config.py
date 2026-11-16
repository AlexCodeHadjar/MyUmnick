"""Секция `[skills]` (Этап 23, ADR-0043): где хранится выбор навыков пользователя."""

from pathlib import Path

from vtuber.kernel import ConfigSection


class SkillsConfig(ConfigSection):
    """Файл выбора — свой у каждого издания: навыки английского издания свои."""

    file: Path

    def resolved(self, root: Path) -> "SkillsConfig":
        """Копия с путём от корня проекта."""
        return self.model_copy(update={"file": root / self.file})
