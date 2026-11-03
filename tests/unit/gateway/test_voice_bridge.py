"""Мост голосового ввода к шлюзу (S-11.3): сообщения UI, ход, замер, перебивание."""

import asyncio
import time

from tests.fakes import FakeClock, FakeLLM
from tests.fakes.conversation import make_conversation
from tests.fakes.recording_sink import RecordingSink
from vtuber.domain import AudioChunk, AudioFormat, CancelReason, MetricRecorded
from vtuber.gateway import (
    END_TO_AUDIO_SPAN,
    InputBargeIn,
    InputFinal,
    InputHypothesis,
    OutboundMessage,
    VoiceBridge,
)
from vtuber.gateway.voice_bridge import _FirstAudioSink
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


async def _flush(telemetry: Telemetry) -> None:
    pump = asyncio.create_task(telemetry.run())
    for _ in range(5):
        await asyncio.sleep(0)
    pump.cancel()
    await asyncio.gather(pump, return_exceptions=True)


async def test_first_audio_is_measured_once_from_end_of_speech() -> None:
    bus = EventBus()
    telemetry = Telemetry(bus, FakeClock())
    recorded: list[MetricRecorded] = []

    async def on_metric(metric: MetricRecorded) -> None:
        recorded.append(metric)

    bus.subscribe(MetricRecorded, on_metric)
    inner = RecordingSink()
    ended_ns = time.perf_counter_ns()
    sink = _FirstAudioSink(inner, telemetry, ended_ns)
    chunk = AudioChunk(AudioFormat(sample_rate=16000), b"\x00\x00")

    await sink.text("Да")
    await sink.audio(chunk)
    await sink.audio(chunk)
    await sink.done()
    await _flush(telemetry)

    assert [metric.name for metric in recorded] == [END_TO_AUDIO_SPAN]
    assert recorded[0].duration_ns >= 0
    assert inner.kinds() == ["text", "audio", "audio", "done"]
