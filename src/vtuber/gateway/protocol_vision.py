"""Протокол: реплика с картинкой (ADR-0024). Отдельное сообщение: `chat.send` остаётся прежним."""

from typing import Final, Literal

from pydantic import Field

from vtuber.gateway.protocol_base import PROTOCOL_VERSION, ProtocolModel, Version

MAX_IMAGE_CHARS: Final = 6 * 1024 * 1024


class ImageData(ProtocolModel):
    """Картинка; UI уменьшает её заранее."""

    mime: Literal["image/jpeg", "image/png", "image/webp"]
    base64: str = Field(min_length=1, max_length=MAX_IMAGE_CHARS)


class SendImageData(ProtocolModel):
    """Реплика с картинкой."""

    text: str = Field(min_length=1)
    image: ImageData


class ChatSendImage(ProtocolModel):
    """UI → Ядро: новая реплика с картинкой; прерывает текущий ход, как `chat.send`."""

    v: Version = PROTOCOL_VERSION
    type: Literal["chat.send_image"]
    data: SendImageData
