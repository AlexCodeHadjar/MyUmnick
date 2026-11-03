"""Протокол: что ядру надо знать об окне UI."""

from typing import Literal

from vtuber.gateway.protocol_base import PROTOCOL_VERSION, ProtocolModel, Version


class VisibilityData(ProtocolModel):
    """Видно ли окно."""

    visible: bool


class WindowVisibility(ProtocolModel):
    """UI → Ядро: окно свернули или вернули; свёрнутому персонаж сам не заговорит (S-15.1)."""

    v: Version = PROTOCOL_VERSION
    type: Literal["window.visibility"]
    data: VisibilityData
