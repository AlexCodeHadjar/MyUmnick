"""Сообщения о ветках диалога (S-16.1)."""

from typing import Literal, Self

from vtuber.gateway.protocol_base import PROTOCOL_VERSION, ProtocolModel, Version


class BranchGoData(ProtocolModel):
    """К какой реплике вернуться."""

    turn: str


class BranchGo(ProtocolModel):
    """UI → Ядро: вернуться к реплике; следующая реплика начнёт новую ветку."""

    v: Version
    type: Literal["branch.go"]
    data: BranchGoData


class BranchCheckpointData(ProtocolModel):
    """Имя контрольной точки."""

    name: str


class BranchCheckpoint(ProtocolModel):
    """UI → Ядро: запомнить текущее место под именем."""

    v: Version
    type: Literal["branch.checkpoint"]
    data: BranchCheckpointData


class BranchMessageData(ProtocolModel):
    """Реплика активной ветки; у реплик пользователя `turn` — None."""

    role: Literal["user", "assistant"]
    text: str
    turn: str | None


class BranchData(ProtocolModel):
    """Ветка: её последняя реплика и длина; `active` — текущий путь идёт через неё."""

    leaf: str
    title: str
    length: int
    active: bool


class CheckpointData(ProtocolModel):
    """Контрольная точка."""

    name: str
    turn: str


class BranchStateData(ProtocolModel):
    """Активный путь, все ветки и контрольные точки."""

    messages: list[BranchMessageData]
    branches: list[BranchData]
    checkpoints: list[CheckpointData]
    problem: str | None


class BranchState(ProtocolModel):
    """Ядро → UI: состояние диалога после перехода или при подключении."""

    v: Version = PROTOCOL_VERSION
    type: Literal["branch.state"] = "branch.state"
    data: BranchStateData

    @classmethod
    def of(
        cls,
        messages: list[BranchMessageData],
        branches: list[BranchData],
        checkpoints: list[CheckpointData],
        problem: str | None,
    ) -> Self:
        """Сообщение о состоянии."""
        return cls(
            data=BranchStateData(
                messages=messages, branches=branches, checkpoints=checkpoints, problem=problem
            )
        )
