"""Навык помощника (Этап 23, ADR-0043): возможность, которую пользователь включает и выключает.

Навык — то, что плагин или ядро регистрирует для хода: справка (`add_context`), команда ведущего,
источник реплик или встроенная возможность (память, инициатива). Id — `<плагин>` или
`<плагин>.<навык>`; встроенные — `core.<навык>`.
"""

from dataclasses import dataclass
from typing import Final

CORE_PLUGIN: Final = "core"
CORE_MEMORY: Final = "core.memory"
CORE_INITIATIVE: Final = "core.initiative"


@dataclass(frozen=True, slots=True)
class SkillInfo:
    """Описание навыка для панели: тексты — на языке издания.

    `network` — навык ходит в интернет (NFR-06: включается только явно); `gpu` — держит модель в
    видеопамяти.
    """

    id: str
    plugin: str
    title: str
    summary: str = ""
    examples: tuple[str, ...] = ()
    network: bool = False
    gpu: bool = False


@dataclass(frozen=True, slots=True)
class SkillStats:
    """Счётчики за сессию: сколько раз навык дал результат, средняя задержка, сколько не успел."""

    uses: int = 0
    total_ms: float = 0.0
    timeouts: int = 0

    @property
    def average_ms(self) -> float | None:
        """Средняя задержка удачного срабатывания; не срабатывал — нет числа."""
        return self.total_ms / self.uses if self.uses else None

    def used(self, ms: float) -> "SkillStats":
        """Ещё одно срабатывание за `ms`."""
        return SkillStats(self.uses + 1, self.total_ms + ms, self.timeouts)

    def timed_out(self) -> "SkillStats":
        """Ещё один выход за срок."""
        return SkillStats(self.uses, self.total_ms, self.timeouts + 1)


@dataclass(frozen=True, slots=True)
class SkillState:
    """Навык в панели: описание, включён ли, загружен ли его плагин, счётчики."""

    info: SkillInfo
    enabled: bool
    loaded: bool
    stats: SkillStats


def plugin_skill(plugin: str, title: str = "", summary: str = "") -> SkillInfo:
    """Навык «весь плагин»: так выглядит плагин, который своих навыков не объявил."""
    return SkillInfo(id=plugin, plugin=plugin, title=title or plugin, summary=summary)
