"""Адаптеры портов для контрактных тестов: каждый — в рабочем и в недоступном состоянии."""

import socket
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager, nullcontext
from dataclasses import dataclass

from tests.fakes import FakeLLM
from tests.llm_stub import LLMStub
from vtuber.adapters.llm import LLMConfig, OpenAICompatLLM
from vtuber.ports import LLMPort

LONG_REPLY = (
    "Привет! Сегодня отличный день, чтобы поболтать о играх, аниме и всяких глупостях. " * 4
)

type AdapterFactory = Callable[[], AbstractAsyncContextManager[LLMPort]]


@dataclass(frozen=True, slots=True)
class LLMCase:
    """Как получить адаптер LLMPort: рабочий (долгий стрим) и с недоступным бэкендом."""

    name: str
    available: AdapterFactory
    unavailable: AdapterFactory


def llm_config(base_url: str) -> LLMConfig:
    """Конфиг для тестов: короткий connect — на Windows закрытый порт отвечает не сразу."""
    return LLMConfig(base_url=base_url, model="stub", connect_timeout_s=0.2, read_timeout_s=5)


def closed_port_url() -> str:
    """Адрес на localhost, где гарантированно никто не слушает."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    return f"http://127.0.0.1:{port}"


@asynccontextmanager
async def _openai_available() -> AsyncIterator[LLMPort]:
    # Порции крупнее: на Windows sleep(0.002) длится ~15 мс (разрешение таймера).
    async with (
        LLMStub(LONG_REPLY, chunk_size=12) as stub,
        OpenAICompatLLM(llm_config(stub.url)) as llm,
    ):
        yield llm


@asynccontextmanager
async def _openai_unavailable() -> AsyncIterator[LLMPort]:
    async with OpenAICompatLLM(llm_config(closed_port_url())) as llm:
        yield llm


def llm_cases() -> list[LLMCase]:
    """Фейк и OpenAI-совместимый адаптер на заглушке; llama.cpp добавляется в S-2.3."""
    return [
        LLMCase(
            name="fake",
            available=lambda: nullcontext(FakeLLM(LONG_REPLY, chunk_size=12, delay_ms=2)),
            unavailable=lambda: nullcontext(FakeLLM(LONG_REPLY, fail_after=0)),
        ),
        LLMCase(name="openai_compat", available=_openai_available, unavailable=_openai_unavailable),
    ]
