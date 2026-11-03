"""Протокол: текст в чате мимо голоса (S-12.6): код не должен звучать."""

from typing import Literal, Self

from vtuber.gateway.protocol_base import PROTOCOL_VERSION, ProtocolModel, Version


class AttachmentData(ProtocolModel):
    """Заголовок и текст."""

    title: str
    text: str


class ChatAttachment(ProtocolModel):
    """Ядро → UI: показать текст отдельным сообщением; озвучки у него нет."""

    v: Version = PROTOCOL_VERSION
    type: Literal["chat.attachment"] = "chat.attachment"
    data: AttachmentData

    @classmethod
    def of(cls, title: str, text: str) -> Self:
        """Текст `text` с заголовком `title`."""
        return cls(data=AttachmentData(title=title, text=text))
