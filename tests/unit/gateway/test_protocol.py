import struct

import pytest
from pydantic import TypeAdapter

from vtuber.domain import (
    AudioChunk,
    AudioFormat,
    BackendState,
    CancelReason,
    Component,
    Emotion,
    ProtocolError,
    TurnId,
)
from vtuber.gateway import (
    AUDIO_FRAME_HEADER_SIZE,
    AUDIO_FRAME_TYPE,
    PROTOCOL_VERSION,
    AvatarEmotion,
    ChatCancel,
    ChatDelta,
    ChatSend,
    ErrorCode,
    ErrorMessage,
    InputTyping,
    MetricsSpan,
    OutboundMessage,
    Status,
    TurnCancelledMessage,
    TurnFinishedMessage,
    TurnStartedMessage,
    decode_audio_frame,
    decode_inbound,
    encode_audio_frame,
    encode_outbound,
    turn_ref,
)

OUTBOUND = TypeAdapter[OutboundMessage](OutboundMessage)
TURN = turn_ref(TurnId(42))


def test_turn_ref_is_zero_padded() -> None:
    assert TURN == "t-000042"


@pytest.mark.parametrize(
    "message",
    [
        TurnStartedMessage.of(TURN),
        ChatDelta.of(TURN, "Привет"),
        AvatarEmotion.of(TURN, Emotion.HAPPY),
        TurnFinishedMessage.of(TURN),
        TurnCancelledMessage.of(TURN, CancelReason.NEW_MESSAGE, ""),
        MetricsSpan.of(TURN, "llm.first_token", 210.5),
        MetricsSpan.of(None, "warmup", 3.0),
        Status.of(Component.LLM, BackendState.READY),
        ErrorMessage.of(TURN, ErrorCode.LLM_UNAVAILABLE, "LLM-сервер не отвечает"),
    ],
    ids=lambda message: message.type,
)
def test_outbound_round_trip(message: OutboundMessage) -> None:
    assert OUTBOUND.validate_json(encode_outbound(message)) == message


def test_envelope_shape_matches_protocol_doc() -> None:
    assert encode_outbound(ChatDelta.of(TURN, "Привет")) == (
        '{"v":1,"type":"chat.delta","turn":"t-000042","data":{"text":"Привет"}}'
    )


def test_inbound_messages_are_parsed_by_type() -> None:
    send = decode_inbound('{"v": 1, "type": "chat.send", "data": {"text": "Привет"}}')
    cancel = decode_inbound('{"v": 1, "type": "chat.cancel", "data": {}}')

    typing = decode_inbound('{"v": 1, "type": "input.typing", "data": {"text": ""}}')

    assert isinstance(send, ChatSend)
    assert send.data.text == "Привет"
    assert isinstance(cancel, ChatCancel)
    assert isinstance(typing, InputTyping)
    assert typing.data.text == ""


@pytest.mark.parametrize(
    "raw",
    [
        "не json",
        '{"v": 1, "type": "chat.unknown", "data": {}}',
        '{"v": 2, "type": "chat.send", "data": {"text": "x"}}',
        '{"v": 1, "type": "chat.send", "data": {}}',
        '{"v": 1, "type": "chat.send", "data": {"text": "x", "extra": 1}}',
        '{"v": 1, "type": "chat.send", "data": {"text": ""}}',
        '{"type": "chat.cancel", "data": {}}',
    ],
)
def test_bad_inbound_is_protocol_error(raw: str) -> None:
    with pytest.raises(ProtocolError):
        decode_inbound(raw)


def test_audio_frame_follows_offset_table() -> None:
    pcm = b"\x01\x02\x03\x04"
    frame = encode_audio_frame(TurnId(42), 7, AudioChunk(AudioFormat(24000), pcm))

    assert frame[0] == AUDIO_FRAME_TYPE == 0x01
    assert frame[1] == PROTOCOL_VERSION
    assert struct.unpack_from("<H", frame, 2) == (7,)
    assert struct.unpack_from("<I", frame, 4) == (24000,)
    assert struct.unpack_from("<Q", frame, 8) == (42,)
    assert frame[AUDIO_FRAME_HEADER_SIZE:] == pcm


def test_audio_frame_round_trip_and_seq_wraps_at_uint16() -> None:
    chunk = AudioChunk(AudioFormat(22050), b"\x00\x10" * 8)

    decoded = decode_audio_frame(encode_audio_frame(TurnId(3), 65536 + 5, chunk))

    assert decoded.turn_id == TurnId(3)
    assert decoded.seq == 5
    assert decoded.chunk == chunk


@pytest.mark.parametrize(
    "frame",
    [b"", b"\x02" + b"\x00" * 15, b"\x01\x09" + b"\x00" * 14, b"\x01\x01\x00"],
)
def test_bad_audio_frame_is_protocol_error(frame: bytes) -> None:
    with pytest.raises(ProtocolError):
        decode_audio_frame(frame)
