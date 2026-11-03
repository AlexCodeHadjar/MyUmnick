"""Протокол: жесты аватара."""

from typing import Literal, Self

from vtuber.domain import Gesture
from vtuber.gateway.protocol_base import PROTOCOL_VERSION, ProtocolModel, Version


class GestureData(ProtocolModel):
    """Какой жест показать."""

    gesture: Gesture


class AvatarGesture(ProtocolModel):
    """Ядро → UI: жест по смыслу фразы; модель без такого жеста его пропускает (S-18.4)."""

    v: Version = PROTOCOL_VERSION
    type: Literal["avatar.gesture"] = "avatar.gesture"
    turn: str
    data: GestureData

    @classmethod
    def of(cls, turn: str, gesture: Gesture) -> Self:
        """Жест `gesture` в ходе `turn`."""
        return cls(turn=turn, data=GestureData(gesture=gesture))
