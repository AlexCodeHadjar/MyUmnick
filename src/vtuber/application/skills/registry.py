"""Реестр навыков (Этап 23, ADR-0043): что включено, что загружено, счётчики за сессию.

Проверка `enabled()` — поиск в словаре: её зовут в горячем пути перед каждым инструментом, и она не
должна стоить ничего заметного (приоритет 1). Выбор пользователя хранится поверх конфига: файл
выбора не переписывает `user.toml`.
"""

from collections.abc import Awaitable, Callable, Iterable, Mapping
from typing import Self

from vtuber.domain import SkillInfo, SkillState, SkillStats
from vtuber.kernel import get_logger
from vtuber.ports import SkillChoicesPort

type LoadPlugin = Callable[[str], Awaitable[tuple[SkillInfo, ...] | None]]
"""Загрузить плагин на ходу; вернёт его навыки или `None`, если он не запустился."""

_log = get_logger(__name__)


class SkillRegistry:
    """Навыки издания. Незагруженный плагин виден как навык «весь плагин», выключенный."""

    def __init__(self, port: SkillChoicesPort, choices: Mapping[str, bool]) -> None:
        self._port = port
        self._choices = dict(choices)
        self._skills: dict[str, SkillInfo] = {}
        self._loaded: dict[str, bool] = {}
        self._stats: dict[str, SkillStats] = {}
        self.load_plugin: LoadPlugin | None = None

    @classmethod
    async def open(cls, port: SkillChoicesPort) -> Self:
        """Реестр с сохранённым выбором пользователя."""
        return cls(port, await port.load())

    def add(self, skills: Iterable[SkillInfo], *, loaded: bool = True) -> None:
        """Навыки запущенного (или найденного, но не загруженного) плагина либо ядра."""
        for info in skills:
            self._skills[info.id] = info
            self._loaded[info.id] = loaded

    def enabled(self, skill_id: str) -> bool:
        """Включён ли навык: выбор пользователя, иначе — включён, если загружен."""
        return self._choices.get(skill_id, self._loaded.get(skill_id, True))

    def offer(self, skills: Iterable[SkillInfo]) -> None:
        """Найденные, но не запущенные плагины: уже известные навыки не перезаписываются."""
        self.add((info for info in skills if info.id not in self._skills), loaded=False)

    def wanted_plugins(self) -> tuple[str, ...]:
        """Плагины, включённые в панели целиком: запустить их при старте вместе с конфигом."""
        return tuple(skill for skill, on in self._choices.items() if on and "." not in skill)

    async def set(self, skill_id: str, *, enabled: bool) -> None:
        """Включить или выключить навык; плагин, которого ещё нет в памяти, загружается.

        Raises:
            ValueError: такого навыка нет.

        """
        info = self._skills.get(skill_id)
        if info is None:
            msg = f"Навыка «{skill_id}» нет"
            raise ValueError(msg)
        if enabled and not self._loaded.get(skill_id, True):
            await self._load(info.plugin)
        self._choices[skill_id] = enabled
        await self._port.save(self._choices)
        _log.info("skills.changed", skill=skill_id, enabled=enabled)

    def record(self, skill_id: str, ms: float | None) -> None:
        """Навык дал результат за `ms`, или (`None`) не успел в срок."""
        stats = self._stats.get(skill_id, SkillStats())
        self._stats[skill_id] = stats.timed_out() if ms is None else stats.used(ms)

    def states(self) -> tuple[SkillState, ...]:
        """Навыки для панели: сначала ядро, потом плагины по имени."""
        ordered = sorted(self._skills.values(), key=lambda info: (info.plugin != "core", info.id))
        return tuple(
            SkillState(
                info=info,
                enabled=self.enabled(info.id),
                loaded=self._loaded.get(info.id, True),
                stats=self._stats.get(info.id, SkillStats()),
            )
            for info in ordered
        )

    async def _load(self, plugin: str) -> None:
        loaded = None if self.load_plugin is None else await self.load_plugin(plugin)
        if loaded is None:
            msg = f"Плагин «{plugin}» не запустился — подробности в журнале"
            raise ValueError(msg)
        self._skills.pop(plugin, None)
        self._loaded.pop(plugin, None)
        self.add(loaded)
