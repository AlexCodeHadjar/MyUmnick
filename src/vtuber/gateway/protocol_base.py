"""Основа протокола: версия и база моделей; сообщения — в `protocol.py` и `protocol_extras.py`."""

from typing import Final, Literal

from pydantic import BaseModel, ConfigDict

PROTOCOL_VERSION: Final = 1

type Version = Literal[1]
"""Версия в каждом конверте; меняется вместе с `PROTOCOL_VERSION` при несовместимом изменении."""


class ProtocolModel(BaseModel):
    """База сообщений: неизменяемы, лишнее поле — ошибка протокола."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class EmptyData(ProtocolModel):
    """Сообщение без полезной нагрузки."""
