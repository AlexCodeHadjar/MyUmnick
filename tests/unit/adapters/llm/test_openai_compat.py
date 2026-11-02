import json
from collections.abc import Callable

import httpx
import pytest

from vtuber.adapters.llm import GenerationConfig, LlamaCppOptions, LLMConfig, OpenAICompatLLM
from vtuber.domain import GenerationFailed, LLMUnavailable, Message, Role
from vtuber.ports import GenerationParams

CFG = LLMConfig(
    base_url="http://llm.test",
    model="local",
    connect_timeout_s=1,
    read_timeout_s=5,
    llamacpp=LlamaCppOptions(slot_id=0, enable_thinking=False, forbid_foreign_scripts=True),
    backend="llamacpp",
    generation=GenerationConfig(max_tokens=64, temperature=0.5),
)
MESSAGES = (Message(Role.SYSTEM, "Ты Мика."), Message(Role.USER, "Привет!"))
PARAMS = GenerationParams(max_tokens=32, temperature=0.5)

type Handler = Callable[[httpx.Request], httpx.Response]


def _sse(*events: str) -> httpx.Response:
    return httpx.Response(200, content="".join(f"data: {event}\n\n" for event in events))


def _chunk(text: str) -> str:
    return json.dumps({"choices": [{"delta": {"content": text}}]})


async def _collect(handler: Handler, params: GenerationParams = PARAMS) -> list[str]:
    async with OpenAICompatLLM(CFG, transport=httpx.MockTransport(handler)) as llm:
        return [delta async for delta in llm.stream(MESSAGES, params)]


async def test_request_is_streaming_chat_completion_with_messages_and_params() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _sse("[DONE]")

    await _collect(handler)

    [request] = seen
    assert request.url == "http://llm.test/v1/chat/completions"
    assert json.loads(request.content) == {
        "model": "local",
        "messages": [
            {"role": "system", "content": "Ты Мика."},
            {"role": "user", "content": "Привет!"},
        ],
        "stream": True,
        "max_tokens": 32,
        "temperature": 0.5,
    }


async def test_stop_strings_are_sent_only_when_given() -> None:
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return _sse("[DONE]")

    await _collect(handler, GenerationParams(max_tokens=8, temperature=0, stop=("\n\n",)))

    assert bodies[0]["stop"] == ["\n\n"]


async def test_deltas_come_in_order_and_stop_at_done() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        role_only = json.dumps({"choices": [{"delta": {"role": "assistant"}}]})
        return _sse(role_only, _chunk("При"), _chunk("вет"), "[DONE]", _chunk("лишнее"))

    assert await _collect(handler) == ["При", "вет"]


async def test_model_loading_status_means_unavailable() -> None:
    with pytest.raises(LLMUnavailable, match="загружает"):
        await _collect(lambda _: httpx.Response(503, text="Loading model"))


async def test_other_error_status_is_generation_failure_with_server_text() -> None:
    with pytest.raises(GenerationFailed, match=r"500.*context too long"):
        await _collect(lambda _: httpx.Response(500, text="context too long"))


async def test_connection_refused_is_unavailable_with_hint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(LLMUnavailable, match=r"llm\.test.*start_llm"):
        await _collect(handler)


async def test_broken_stream_is_generation_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.RemoteProtocolError("peer closed", request=request)

    with pytest.raises(GenerationFailed):
        await _collect(handler)


async def test_prefill_checks_that_server_answers() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(200, json={"data": []})

    async with OpenAICompatLLM(CFG, transport=httpx.MockTransport(handler)) as llm:
        await llm.prefill(MESSAGES)

    assert paths == ["/v1/models"]


async def test_prefill_on_error_status_is_unavailable() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(503))

    async with OpenAICompatLLM(CFG, transport=transport) as llm:
        with pytest.raises(LLMUnavailable):
            await llm.prefill(MESSAGES)
