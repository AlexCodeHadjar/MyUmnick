"""Протокол: что ядру надо знать об окне UI."""

from typing import Literal, Self

from vtuber.gateway.protocol_base import PROTOCOL_VERSION, ProtocolModel, Version


class VisibilityData(ProtocolModel):
    """Видно ли окно."""

    visible: bool


class WindowVisibility(ProtocolModel):
    """UI → Ядро: окно свернули или вернули; свёрнутому персонаж сам не заговорит (S-15.1)."""

    v: Version = PROTOCOL_VERSION
    type: Literal["window.visibility"]
    data: VisibilityData


class EditionData(ProtocolModel):
    """Издание ядра (Этап 20, ADR-0032): язык интерфейса и профиль содержания."""

    id: str
    language: str
    content_profile: str
    stream_safe: bool


class AppEdition(ProtocolModel):
    """Ядро → UI при подключении: в каком издании запущено ядро; UI сверяет с выбором на экране."""

    v: Version = PROTOCOL_VERSION
    type: Literal["app.edition"] = "app.edition"
    data: EditionData

    @classmethod
    def of(cls, edition_id: str, language: str, content_profile: str, *, stream_safe: bool) -> Self:
        """Издание `edition_id` на языке `language`."""
        data = EditionData(
            id=edition_id,
            language=language,
            content_profile=content_profile,
            stream_safe=stream_safe,
        )
        return cls(data=data)
