"""LlamaCppLLM: на заглушке — всегда; против настоящего llama-server — с маркером gpu."""

import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest

from tests.contract.factories import llm_config
from tests.llm_stub import STUB_PROMPT, LLMStub
from vtuber.adapters.llm import LlamaCppLLM
from vtuber.bootstrap import load_app_config
from vtuber.domain import LLMUnavailable, Message, Role
from vtuber.ports import GenerationParams

ROOT = Path(__file__).resolve().parents[2]
MESSAGES = (
    Message(Role.SYSTEM, "Ты дружелюбная ведущая. Отвечай коротко."),
    Message(Role.USER, "Привет! Как дела?"),
)
PARAMS = GenerationParams(max_tokens=48, temperature=0.7)
SLOT_RELEASE_TIMEOUT_S = 1.0
SLOT_POLL_INTERVAL_S = 0.05


async def test_prefill_sends_rendered_template_to_dialog_slot() -> None:
    async with LLMStub("") as stub, LlamaCppLLM(llm_config(stub.url)) as llm:
        await llm.prefill(MESSAGES)

    [completion] = stub.bodies("/completion")
    assert completion == {"prompt": STUB_PROMPT, "n_predict": 0, "cache_prompt": True, "id_slot": 0}


@pytest.fixture
async def real_llm() -> AsyncIterator[LlamaCppLLM]:
    cfg = load_app_config(ROOT, os.environ).llm
    async with LlamaCppLLM(cfg) as llm:
        try:
            await llm.prefill(MESSAGES[:1])
        except LLMUnavailable as exc:
            pytest.skip(f"llama-server не запущен: {exc}")
        yield llm


@pytest.mark.gpu
async def test_real_server_streams_russian_reply(real_llm: LlamaCppLLM) -> None:
    text = "".join([delta async for delta in real_llm.stream(MESSAGES, PARAMS)])

    assert text.strip()
    assert "<think>" not in text


@pytest.mark.gpu
async def test_real_server_frees_dialog_slot_after_cancellation(real_llm: LlamaCppLLM) -> None:
    first_delta = asyncio.Event()

    async def consume() -> None:
        async for _ in real_llm.stream(MESSAGES, GenerationParams(max_tokens=512, temperature=0.7)):
            first_delta.set()

    task = asyncio.create_task(consume())
    await asyncio.wait_for(first_delta.wait(), timeout=30)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)

    cfg = load_app_config(ROOT, os.environ).llm
    async with httpx.AsyncClient(base_url=cfg.base_url, trust_env=False) as client:
        await asyncio.wait_for(_slot_idle(client, cfg.llamacpp.slot_id), SLOT_RELEASE_TIMEOUT_S)


async def _slot_idle(client: httpx.AsyncClient, slot_id: int) -> None:
    while True:
        slots = (await client.get("/slots")).json()
        if not any(slot["id"] == slot_id and slot["is_processing"] for slot in slots):
            return
        await asyncio.sleep(SLOT_POLL_INTERVAL_S)
