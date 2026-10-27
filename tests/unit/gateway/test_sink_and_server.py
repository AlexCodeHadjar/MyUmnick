import pytest

from tests.fakes import FakeClock, FakeLLM
from tests.fakes.conversation import make_conversation
from vtuber.domain import TurnId, TurnStateError
from vtuber.gateway import (
    ChatDelta,
    GatewayConfig,
    GatewayServer,
    OutboundMessage,
    WsReplySink,
)
from vtuber.kernel import EventBus, Telemetry, turn_context


async def test_sink_tags_messages_with_current_turn() -> None:
    sent: list[OutboundMessage] = []

    async def send(message: OutboundMessage) -> None:
        sent.append(message)

    with turn_context(TurnId(5)):
        await WsReplySink(send).text("Привет")

    assert sent == [ChatDelta.of("t-000005", "Привет")]


async def test_sink_outside_turn_is_a_logic_error() -> None:
    async def send(message: OutboundMessage) -> None:
        raise AssertionError(message)

    with pytest.raises(TurnStateError):
        await WsReplySink(send).text("Привет")


def test_port_is_unknown_before_start() -> None:
    bus = EventBus()
    service = make_conversation(FakeLLM("Ок"), bus, Telemetry(bus, FakeClock()))
    server = GatewayServer(service, bus, GatewayConfig(host="127.0.0.1", port=0))

    with pytest.raises(RuntimeError, match="async with"):
        _ = server.port
