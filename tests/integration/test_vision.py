"""Картинка к реплике: доходит до модели, не оседает в истории, отказ понятен (S-18.1)."""

import json
from collections.abc import AsyncIterator
from contextlib import aclosing

import httpx
import pytest

from tests.fakes import FakeClock, FakeLLM, RecordingSink
from tests.fakes.conversation import make_conversation
from vtuber.adapters.llm import LLMConfig, server_arguments
from vtuber.adapters.llm.openai_compat import OpenAICompatLLM, wire_messages
from vtuber.adapters.llm.server_process import LlamaServerConfig
from vtuber.domain import (
    AttachedImage,
    CancelReason,
    Message,
    Role,
    TurnCancelled,
    VisionUnavailable,
)
from vtuber.kernel import EventBus, Telemetry
from vtuber.ports import GenerationParams

IMAGE = AttachedImage("image/jpeg", "QUJD")
PARAMS = GenerationParams(16, 0.5)


def _cfg(base_url: str = "http://llm.test") -> LLMConfig:
    return LLMConfig.model_validate(
        {
            "backend": "openai",
            "base_url": base_url,
            "model": "m",
            "connect_timeout_s": 1.0,
            "read_timeout_s": 1.0,
            "generation": {"max_tokens": 16, "temperature": 0.5},
            "llamacpp": {
                "slot_id": 0,
                "enable_thinking": False,
                "forbid_foreign_scripts": False,
                "forbid_cyrillic": False,
            },
        }
    )


def test_plain_message_stays_a_string_so_ordinary_requests_do_not_change() -> None:
    wire = wire_messages([Message(Role.USER, "Привет")])
    assert wire == [{"role": "user", "content": "Привет"}]


def test_image_goes_as_a_data_url_after_the_text() -> None:
    wire = wire_messages([Message(Role.USER, "Что тут?", (IMAGE,))])
    assert wire[0]["content"] == [
        {"type": "text", "text": "Что тут?"},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,QUJD"}},
    ]


async def _collect(stream: AsyncIterator[str]) -> list[str]:
    return [delta async for delta in stream]


async def test_server_without_vision_gives_a_clear_refusal() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert "image_url" in json.loads(request.content)["messages"][0]["content"][1]["type"]
        return httpx.Response(500, json={"error": {"message": "image input is not supported"}})

    transport = httpx.MockTransport(respond)
    async with OpenAICompatLLM(_cfg(), transport) as llm:
        stream = llm.stream([Message(Role.USER, "Что тут?", (IMAGE,))], PARAMS)
        async with aclosing(stream) as deltas:
            with pytest.raises(VisionUnavailable, match="--mmproj"):
                await _collect(deltas)


async def test_turn_gets_image_and_history_keeps_only_a_note() -> None:
    bus = EventBus()
    llm = FakeLLM("Вижу кота.")
    service = make_conversation(llm, bus, Telemetry(bus, FakeClock()))

    await service.handle("Что тут?", RecordingSink(), images=(IMAGE,))
    await service.wait_idle()
    assert llm.calls[-1][0][-1].images == (IMAGE,)

    await service.handle("А цвет?", RecordingSink())
    await service.wait_idle()
    history = llm.calls[-1][0]
    assert not any(message.images for message in history), "картинка не живёт дольше своего хода"
    assert any("картинк" in message.text for message in history)


async def test_refusal_ends_the_turn_with_its_message() -> None:
    bus = EventBus()
    cancelled: list[TurnCancelled] = []

    async def on_cancel(event: TurnCancelled) -> None:
        cancelled.append(event)

    bus.subscribe(TurnCancelled, on_cancel)
    llm = FakeLLM("x", fail_after=0, error_type=VisionUnavailable)
    service = make_conversation(llm, bus, Telemetry(bus, FakeClock()))
    await service.handle("Что тут?", RecordingSink(), images=(IMAGE,))
    await service.wait_idle()
    assert cancelled[0].reason is CancelReason.ERROR
    assert cancelled[0].message is not None


def test_mmproj_is_passed_only_when_configured() -> None:
    base = {
        "autostart": True,
        "executable": "x.exe",
        "model": "m.gguf",
        "log_file": "l.log",
        "context_size": 1024,
        "slots": 1,
        "ready_timeout_s": 1.0,
        "stop_timeout_s": 1.0,
        "extra_args": (),
    }
    plain = LlamaServerConfig.model_validate(base)
    assert "--mmproj" not in server_arguments(plain, "http://127.0.0.1:8080")
    seeing = LlamaServerConfig.model_validate({**base, "mmproj": "p.gguf"})
    args = server_arguments(seeing, "http://127.0.0.1:8080")
    assert args[args.index("--mmproj") + 1] == "p.gguf"
