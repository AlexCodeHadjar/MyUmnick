"""Протокол навыков (Этап 23, ADR-0043): список навыков помощника и их переключение."""

from typing import Literal, Self

from vtuber.domain import SkillState
from vtuber.gateway.protocol_base import PROTOCOL_VERSION, ProtocolModel, Version


class SkillsActionData(ProtocolModel):
    """`list` — прислать список (и найти установленные плагины); `set` — включить или выключить."""

    action: Literal["list", "set"]
    id: str | None = None
    enabled: bool | None = None


class SkillsAction(ProtocolModel):
    """UI → Ядро: действие в панели «Навыки»."""

    v: Version
    type: Literal["skills.action"]
    data: SkillsActionData


class SkillData(ProtocolModel):
    """Навык в панели: тексты на языке издания, флаги, состояние и счётчики за сессию.

    `loaded = false` — плагин установлен, но не запущен: включение запустит его на ходу.
    """

    id: str
    plugin: str
    title: str
    summary: str
    examples: list[str]
    network: bool
    gpu: bool
    enabled: bool
    loaded: bool
    uses: int
    average_ms: float | None
    timeouts: int


class SkillsData(ProtocolModel):
    """Все навыки; `problem` — почему не получилось последнее действие."""

    skills: list[SkillData]
    problem: str | None


class SkillsState(ProtocolModel):
    """Ядро → UI: список навыков по запросу и после переключения."""

    v: Version = PROTOCOL_VERSION
    type: Literal["skills.state"] = "skills.state"
    data: SkillsData

    @classmethod
    def of(cls, states: tuple[SkillState, ...], problem: str | None = None) -> Self:
        """Состояние из реестра."""
        skills = [
            SkillData(
                id=state.info.id,
                plugin=state.info.plugin,
                title=state.info.title,
                summary=state.info.summary,
                examples=list(state.info.examples),
                network=state.info.network,
                gpu=state.info.gpu,
                enabled=state.enabled,
                loaded=state.loaded,
                uses=state.stats.uses,
                average_ms=state.stats.average_ms,
                timeouts=state.stats.timeouts,
            )
            for state in states
        ]
        return cls(data=SkillsData(skills=skills, problem=problem))
