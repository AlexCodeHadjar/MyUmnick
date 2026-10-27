"""OpenAICompatLLM против настоящего сокета: заглушка на localhost (без GPU)."""

import asyncio

from tests.contract.factories import llm_config
from tests.llm_stub import CHAT_PATH, LLMStub
from vtuber.adapters.llm import OpenAICompatLLM
from vtuber.domain import Message, Role
from vtuber.ports import GenerationParams

MESSAGES = (Message(Role.USER, "Привет"),)
PARAMS = GenerationParams(max_tokens=16, temperature=0.2)


async def test_full_reply_arrives_and_request_reaches_server() -> None:
    async with LLMStub("Привет-привет!") as stub, OpenAICompatLLM(llm_config(stub.url)) as llm:
        text = "".join([delta async for delta in llm.stream(MESSAGES, PARAMS)])

    assert text == "Привет-привет!"
    [body] = stub.bodies(CHAT_PATH)
    assert isinstance(body, dict)
    assert body["messages"] == [{"role": "user", "content": "Привет"}]
    assert body["stream"] is True


async def test_cancelling_consumer_closes_connection_so_server_stops() -> None:
    first_delta = asyncio.Event()

    async with (
        LLMStub("слово " * 500, delay_s=0.005) as stub,
        OpenAICompatLLM(llm_config(stub.url)) as llm,
    ):

        async def consume() -> None:
            async for _ in llm.stream(MESSAGES, PARAMS):
                first_delta.set()

        task = asyncio.create_task(consume())
        await asyncio.wait_for(first_delta.wait(), timeout=5)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

        await asyncio.wait_for(stub.client_gone.wait(), timeout=1)
