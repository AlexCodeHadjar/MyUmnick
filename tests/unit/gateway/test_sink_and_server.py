import pytest

from tests.fakes import FakeClock, FakeLLM
from tests.fakes.conversation import make_conversation
from vtuber.domain import AudioChunk, AudioFormat, TurnId, TurnStateError
from vtuber.gateway import (
    ChatDelta,
    GatewayConfig,
    GatewayServer,
    OutboundMessage,
    WsReplySink,
    decode_audio_frame,
)
from vtuber.kernel import EventBus, Telemetry, turn_context


async def test_sink_tags_messages_with_current_turn() -> None:
    sent: list[OutboundMessage] = []

    async def send(message: OutboundMessage) -> None:
        sent.append(message)

    with turn_context(TurnId(5)):
        await WsReplySink(send, _no_bytes).text("Привет")

    assert sent == [ChatDelta.of("t-000005", "Привет")]


async def _no_bytes(frame: bytes) -> None:
    raise AssertionError(frame)


async def test_sink_sends_audio_as_numbered_binary_frames_of_current_turn() -> None:
    frames: list[bytes] = []

    async def send(message: OutboundMessage) -> None:
        raise AssertionError(message)

    async def send_bytes(frame: bytes) -> None:
        frames.append(frame)

    chunk = AudioChunk(AudioFormat(48000), b"\0\0")
    with turn_context(TurnId(7)):
        sink = WsReplySink(send, send_bytes)
        await sink.audio(chunk)
        await sink.audio(chunk)

    decoded = [decode_audio_frame(frame) for frame in frames]
    assert [(f.turn_id, f.seq, f.chunk) for f in decoded] == [(7, 0, chunk), (7, 1, chunk)]


async def test_sink_outside_turn_is_a_logic_error() -> None:
    async def send(message: OutboundMessage) -> None:
        raise AssertionError(message)

    with pytest.raises(TurnStateError):
        await WsReplySink(send, _no_bytes).text("Привет")


def test_port_is_unknown_before_start() -> None:
    bus = EventBus()
    service = make_conversation(FakeLLM("Ок"), bus, Telemetry(bus, FakeClock()))
    server = GatewayServer(service, bus, GatewayConfig(host="127.0.0.1", port=0))

    with pytest.raises(RuntimeError, match="async with"):
        _ = server.port
