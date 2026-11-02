"""Кодек протокола: JSON-сообщения и бинарные аудиокадры (без base64 — экономия ~33 %)."""

import struct
from dataclasses import dataclass
from typing import Final

from pydantic import TypeAdapter, ValidationError

from vtuber.domain import SAMPLE_WIDTH_BYTES, AudioChunk, AudioFormat, ProtocolError, TurnId
from vtuber.gateway.protocol import PROTOCOL_VERSION, InboundMessage, OutboundMessage

AUDIO_FRAME_TYPE: Final = 0x01
_AUDIO_HEADER: Final = struct.Struct("<BBHIQ")  # тип, версия, seq, sample_rate, turn_id (LE)
AUDIO_FRAME_HEADER_SIZE: Final = _AUDIO_HEADER.size
MIC_FRAME_TYPE: Final = 0x02
_MIC_HEADER: Final = struct.Struct("<BBHI")  # тип, версия, seq, sample_rate (LE)
MIC_FRAME_HEADER_SIZE: Final = _MIC_HEADER.size
_SEQ_MODULO: Final = 1 << 16
_INBOUND: Final = TypeAdapter[InboundMessage](InboundMessage)


@dataclass(frozen=True, slots=True)
class AudioFrame:
    """Разобранный аудиокадр."""

    turn_id: TurnId
    seq: int
    chunk: AudioChunk


@dataclass(frozen=True, slots=True)
class MicFrame:
    """Разобранный кадр микрофона: PCM s16le моно от UI (Этап 11)."""

    seq: int
    chunk: AudioChunk


def encode_mic_frame(seq: int, chunk: AudioChunk) -> bytes:
    """Кадр микрофона: 8 байт заголовка + PCM; так его собирает UI (`core/frames.ts`)."""
    return (
        _MIC_HEADER.pack(
            MIC_FRAME_TYPE, PROTOCOL_VERSION, seq % _SEQ_MODULO, chunk.format.sample_rate
        )
        + chunk.pcm
    )


def decode_mic_frame(frame: bytes) -> MicFrame:
    """Разбирает бинарный кадр от UI; проверка один раз на границе.

    Raises:
        ProtocolError: кадр короче заголовка, другой тип или версия, нецелое число сэмплов.

    """
    if len(frame) < MIC_FRAME_HEADER_SIZE:
        msg = f"Кадр микрофона короче заголовка ({len(frame)} < {MIC_FRAME_HEADER_SIZE})"
        raise ProtocolError(msg)
    kind, version, seq, sample_rate = _MIC_HEADER.unpack_from(frame)
    if (kind, version) != (MIC_FRAME_TYPE, PROTOCOL_VERSION):
        msg = f"Неизвестный бинарный кадр: тип {kind:#04x}, версия {version}"
        raise ProtocolError(msg)
    pcm = frame[MIC_FRAME_HEADER_SIZE:]
    if sample_rate == 0 or len(pcm) % SAMPLE_WIDTH_BYTES:
        msg = f"Кадр микрофона: частота {sample_rate}, байт PCM {len(pcm)}"
        raise ProtocolError(msg)
    return MicFrame(seq, AudioChunk(AudioFormat(sample_rate), pcm))


def decode_inbound(raw: str | bytes) -> InboundMessage:
    """Сообщение от UI; проверка один раз на границе (принцип 6 архитектуры).

    Raises:
        ProtocolError: не JSON, неизвестный тип, другая версия или неверные поля.

    """
    try:
        return _INBOUND.validate_json(raw)
    except ValidationError as exc:
        problems = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
        msg = f"Сообщение не по протоколу v{PROTOCOL_VERSION}: {problems}"
        raise ProtocolError(msg) from exc


def encode_outbound(message: OutboundMessage) -> str:
    """JSON-строка сообщения для UI (сериализация pydantic-core, без лишних пробелов)."""
    return message.model_dump_json()


def encode_audio_frame(turn_id: TurnId, seq: int, chunk: AudioChunk) -> bytes:
    """Бинарный кадр: 16 байт заголовка + PCM s16le моно; `seq` по модулю 2^16."""
    header = _AUDIO_HEADER.pack(
        AUDIO_FRAME_TYPE, PROTOCOL_VERSION, seq % _SEQ_MODULO, chunk.format.sample_rate, turn_id
    )
    return header + chunk.pcm


def decode_audio_frame(frame: bytes) -> AudioFrame:
    """Разбирает аудиокадр (тесты; кадры микрофона — Этап 11).

    Raises:
        ProtocolError: кадр короче заголовка, другой тип или версия.

    """
    if len(frame) < AUDIO_FRAME_HEADER_SIZE:
        msg = f"Аудиокадр короче заголовка ({len(frame)} < {AUDIO_FRAME_HEADER_SIZE} байт)"
        raise ProtocolError(msg)
    kind, version, seq, sample_rate, turn_id = _AUDIO_HEADER.unpack_from(frame)
    if (kind, version) != (AUDIO_FRAME_TYPE, PROTOCOL_VERSION):
        msg = f"Неизвестный кадр: тип {kind:#04x}, версия {version}"
        raise ProtocolError(msg)
    pcm = frame[AUDIO_FRAME_HEADER_SIZE:]
    return AudioFrame(TurnId(turn_id), seq, AudioChunk(AudioFormat(sample_rate), pcm))
