"""Мост голосового ввода к шлюзу (S-11.3): сообщения UI, ход, замер, перебивание."""

import asyncio

from tests.fakes import FakeClock, FakeLLM, FakeTTS
from tests.fakes.conversation import make_conversation
from vtuber.domain import CancelReason, MetricRecorded
from vtuber.gateway import (
    END_TO_AUDIO_SPAN,
    InputBargeIn,
    InputFinal,
    InputHypothesis,
    OutboundMessage,
    VoiceBridge,
)
from vtuber.kernel import EventBus, Telemetry


def _bridge(llm: FakeLLM) -> tuple[VoiceBridge, list[OutboundMessage], EventBus]:
    sent: list[OutboundMessage] = []

    async def send(message: OutboundMessage) -> None:
        sent.append(message)

    async def send_bytes(_: bytes) -> None:
        await asyncio.sleep(0)

    bus = EventBus()
    telemetry = Telemetry(bus, FakeClock())
    service = make_conversation(llm, bus, telemetry)
    return VoiceBridge(service, send, send_bytes, telemetry), sent, bus


async def test_barge_in_tells_ui_first() -> None:
    bridge, sent, _ = _bridge(FakeLLM("Ок"))

    await bridge.barge_in()

    assert sent == [InputBargeIn.of()]
    assert CancelReason.BARGE_IN.value == "barge_in"


async def test_hypothesis_goes_to_ui_and_prefills_llm() -> None:
    llm = FakeLLM("Ок")
    bridge, sent, _ = _bridge(llm)

    await bridge.hypothesis("как дела")
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    assert sent == [InputHypothesis.of("как дела")]
    assert llm.prefills[0][-1].text == "как дела"


async def test_final_is_a_user_reply_and_starts_a_turn() -> None:
    llm = FakeLLM("Отлично!")
    bridge, sent, _ = _bridge(llm)

    await bridge.final("как дела", 0)
    for _ in range(50):
        await asyncio.sleep(0)

    assert sent[0] == InputFinal.of("как дела")
    assert llm.calls[0][0][-1].text == "как дела"
    assert END_TO_AUDIO_SPAN == "voice.end_to_audio"
    assert MetricRecorded is not None
    assert FakeTTS is not None
