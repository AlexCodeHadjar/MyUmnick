"""Шлюз на настоящем WebSocket (localhost) с FakeLLM: протокол, отмена, один клиент, задержка."""

import asyncio
import json
import time
from collections.abc import AsyncGenerator, AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

import pytest
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed

from tests.fakes import FakeClock, FakeLLM
from tests.fakes.conversation import make_conversation
from tools.bench_latency import percentile
from vtuber.domain import (
    AudioChunk,
    AudioFormat,
    BackendState,
    BackendStatusChanged,
    Component,
    Message,
    MetricRecorded,
    TurnId,
)
from vtuber.gateway import REPLACED_CODE, GatewayConfig, GatewayServer, encode_mic_frame
from vtuber.kernel import EventBus, Telemetry
from vtuber.ports import GenerationParams, LLMPort

LATENCY_LIMIT_MS = 3.0
SEND = json.dumps({"v": 1, "type": "chat.send", "data": {"text": "Привет"}})
CANCEL = json.dumps({"v": 1, "type": "chat.cancel", "data": {}})


@dataclass(slots=True)
class _Gateway:
    server: GatewayServer
    bus: EventBus

    def url(self) -> str:
        return f"ws://127.0.0.1:{self.server.port}"


@asynccontextmanager
async def _gateway(llm: LLMPort) -> AsyncIterator[_Gateway]:
    bus = EventBus()
    service = make_conversation(llm, bus, Telemetry(bus, FakeClock()))
    async with GatewayServer(service, bus, GatewayConfig(host="127.0.0.1", port=0)) as server:
        yield _Gateway(server, bus)


async def _messages_until(ws: ClientConnection, final_type: str) -> list[dict[str, object]]:
    received: list[dict[str, object]] = []
    while not received or received[-1]["type"] != final_type:
        received.append(json.loads(await asyncio.wait_for(ws.recv(), timeout=2)))
    return received


async def test_chat_send_streams_turn_over_websocket() -> None:
    async with (
        _gateway(FakeLLM("<happy>Привет-привет!", chunk_size=4)) as gw,
        connect(gw.url()) as ws,
    ):
        await ws.send(SEND)
        messages = await _messages_until(ws, "turn.finished")

    kinds = [m["type"] for m in messages]
    assert kinds[0] == "turn.started"
    assert kinds[-1] == "turn.finished"
    assert "avatar.emotion" in kinds
    text = "".join(m["data"]["text"] for m in messages if m["type"] == "chat.delta")  # type: ignore[index]
    assert text == "Привет-привет!"
    assert {m.get("turn") for m in messages} == {"t-000001"}


@dataclass(slots=True)
class _PrefillLLM:
    """Запоминает прогревы; ответ — как у FakeLLM."""

    prefills: list[Sequence[Message]] = field(default_factory=list)
    warmed: asyncio.Event = field(default_factory=asyncio.Event)

    async def stream(
        self, messages: Sequence[Message], params: GenerationParams
    ) -> AsyncGenerator[str]:
        yield "Ок."

    async def prefill(self, messages: Sequence[Message]) -> None:
        self.prefills.append(messages)
        self.warmed.set()


async def test_input_typing_prefills_llm_without_reply() -> None:
    llm = _PrefillLLM()
    typing = json.dumps({"v": 1, "type": "input.typing", "data": {"text": "Расскажи про"}})
    async with _gateway(llm) as gw, connect(gw.url()) as ws:
        await ws.send(typing)
        await asyncio.wait_for(llm.warmed.wait(), timeout=2)
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(ws.recv(), timeout=0.1)

    assert llm.prefills[0][-1].text == "Расскажи про"


async def test_mic_frames_reach_the_sink_in_order() -> None:
    received: list[AudioChunk] = []
    done = asyncio.Event()

    async def sink(chunk: AudioChunk) -> None:
        received.append(chunk)
        if len(received) == 2:
            done.set()

    chunks = [AudioChunk(AudioFormat(16_000), bytes([i]) * 640) for i in range(2)]
    async with _gateway(FakeLLM("Ок")) as gw, connect(gw.url()) as ws:
        gw.server.on_mic(sink)
        for seq, chunk in enumerate(chunks):
            await ws.send(encode_mic_frame(seq, chunk))
        await asyncio.wait_for(done.wait(), timeout=2)

    assert received == chunks


async def test_bad_message_gets_error_and_connection_survives() -> None:
    async with _gateway(FakeLLM("Ок")) as gw, connect(gw.url()) as ws:
        await ws.send("не json")
        error = json.loads(await asyncio.wait_for(ws.recv(), timeout=2))
        await ws.send(b"\x01\x02")
        binary_error = json.loads(await asyncio.wait_for(ws.recv(), timeout=2))
        await ws.send(SEND)
        messages = await _messages_until(ws, "turn.finished")

    assert error["type"] == "error"
    assert error["data"]["code"] == "bad_message"
    assert binary_error["data"]["code"] == "bad_message"
    assert messages[-1]["type"] == "turn.finished"


@dataclass(slots=True)
class _EndlessLLM:
    """Первая порция — и ждёт вечно (пока ход не отменят)."""

    closed: asyncio.Event = field(default_factory=asyncio.Event)

    async def stream(
        self, messages: Sequence[Message], params: GenerationParams
    ) -> AsyncGenerator[str]:
        try:
            yield "Жила-"
            await asyncio.Event().wait()
        finally:
            self.closed.set()

    async def prefill(self, messages: Sequence[Message]) -> None:
        """Не нужен."""


async def test_chat_cancel_stops_the_turn() -> None:
    llm = _EndlessLLM()
    async with _gateway(llm) as gw, connect(gw.url()) as ws:
        await ws.send(SEND)
        await _messages_until(ws, "chat.delta")
        await ws.send(CANCEL)
        cancelled = (await _messages_until(ws, "turn.cancelled"))[-1]

    assert cancelled["data"] == {"reason": "user_stop", "message": ""}
    assert llm.closed.is_set()


async def test_new_client_replaces_old_one() -> None:
    async with (
        _gateway(FakeLLM("Ок")) as gw,
        connect(gw.url()) as first,
        connect(gw.url()) as second,
    ):
        with pytest.raises(ConnectionClosed) as closed:
            await asyncio.wait_for(first.recv(), timeout=2)
        await second.send(SEND)
        messages = await _messages_until(second, "turn.finished")

    assert closed.value.rcvd is not None
    assert closed.value.rcvd.code == REPLACED_CODE
    assert messages[-1]["type"] == "turn.finished"


async def test_disconnect_mid_turn_cancels_it() -> None:
    llm = _EndlessLLM()
    async with _gateway(llm) as gw:
        async with connect(gw.url()) as ws:
            await ws.send(SEND)
            await _messages_until(ws, "chat.delta")
        await asyncio.wait_for(llm.closed.wait(), timeout=2)


async def test_metrics_and_status_reach_the_client() -> None:
    async with _gateway(FakeLLM("Ок")) as gw:
        await gw.bus.publish(BackendStatusChanged(Component.LLM, BackendState.READY))
        async with connect(gw.url()) as ws:
            status = json.loads(await asyncio.wait_for(ws.recv(), timeout=2))  # при подключении
            await gw.bus.publish(MetricRecorded("llm.first_token", 210_500_000, TurnId(7)))
            metric = json.loads(await asyncio.wait_for(ws.recv(), timeout=2))

    assert status == {"v": 1, "type": "status", "data": {"component": "llm", "state": "ready"}}
    assert metric["turn"] == "t-000007"
    assert metric["data"] == {"name": "llm.first_token", "ms": 210.5}


@dataclass(slots=True)
class _TimedLLM:
    """Отдаёт `count` порций и помнит момент отдачи каждой (perf_counter_ns)."""

    count: int
    sent_at: list[int] = field(default_factory=list)

    async def stream(
        self, messages: Sequence[Message], params: GenerationParams
    ) -> AsyncGenerator[str]:
        for index in range(self.count):
            await asyncio.sleep(0.001)
            self.sent_at.append(time.perf_counter_ns())
            yield f"{index} "

    async def prefill(self, messages: Sequence[Message]) -> None:
        """Не нужен."""


async def test_delta_reaches_client_within_3_ms_p95() -> None:
    llm = _TimedLLM(count=60)
    received_at: list[int] = []
    async with _gateway(llm) as gw, connect(gw.url()) as ws:
        await ws.send(SEND)
        while True:
            message = json.loads(await asyncio.wait_for(ws.recv(), timeout=2))
            if message["type"] == "chat.delta":
                received_at.append(time.perf_counter_ns())
            if message["type"] == "turn.finished":
                break

    latencies = [
        (got - sent) / 1_000_000 for sent, got in zip(llm.sent_at, received_at, strict=True)
    ]
    assert percentile(latencies, 0.95) <= LATENCY_LIMIT_MS, latencies
