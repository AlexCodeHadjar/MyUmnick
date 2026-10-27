"""Адаптеры портов для контрактных тестов: каждый — в рабочем и в недоступном состоянии."""

import socket
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager, nullcontext
from dataclasses import dataclass

from tests.fakes import FakeLLM, FakeTTS
from tests.llm_stub import LLMStub
from vtuber.adapters.llm import (
    GenerationConfig,
    LlamaCppLLM,
    LlamaCppOptions,
    LLMConfig,
    OpenAICompatLLM,
)
from vtuber.ports import LLMPort, TTSPort

LONG_REPLY = (
    "Привет! Сегодня отличный день, чтобы поболтать о играх, аниме и всяких глупостях. " * 4
)

type AdapterFactory = Callable[[], AbstractAsyncContextManager[LLMPort]]
type HttpAdapter = type[OpenAICompatLLM]


@dataclass(frozen=True, slots=True)
class LLMCase:
    """Как получить адаптер LLMPort: рабочий (долгий стрим) и с недоступным бэкендом."""

    name: str
    available: AdapterFactory
    unavailable: AdapterFactory


def llm_config(base_url: str) -> LLMConfig:
    """Конфиг для тестов: короткий connect — на Windows закрытый порт отвечает не сразу."""
    return LLMConfig(
        base_url=base_url,
        model="stub",
        connect_timeout_s=0.2,
        read_timeout_s=5,
        llamacpp=LlamaCppOptions(slot_id=0, enable_thinking=False),
        backend="llamacpp",
        generation=GenerationConfig(max_tokens=64, temperature=0.5),
    )


def closed_port_url() -> str:
    """Адрес на localhost, где гарантированно никто не слушает."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    return f"http://127.0.0.1:{port}"


def _on_stub(adapter: HttpAdapter) -> AdapterFactory:
    @asynccontextmanager
    async def factory() -> AsyncIterator[LLMPort]:
        # Порции крупнее: на Windows sleep(0.002) длится ~15 мс (разрешение таймера).
        async with (
            LLMStub(LONG_REPLY, chunk_size=12) as stub,
            adapter(llm_config(stub.url)) as llm,
        ):
            yield llm

    return factory


def _on_closed_port(adapter: HttpAdapter) -> AdapterFactory:
    @asynccontextmanager
    async def factory() -> AsyncIterator[LLMPort]:
        async with adapter(llm_config(closed_port_url())) as llm:
            yield llm

    return factory


def llm_cases() -> list[LLMCase]:
    """Фейк и HTTP-адаптеры на заглушке llama-server/OpenAI API."""
    http_adapters: dict[str, HttpAdapter] = {
        "openai_compat": OpenAICompatLLM,
        "llamacpp": LlamaCppLLM,
    }
    return [
        LLMCase(
            name="fake",
            available=lambda: nullcontext(FakeLLM(LONG_REPLY, chunk_size=12, delay_ms=2)),
            unavailable=lambda: nullcontext(FakeLLM(LONG_REPLY, fail_after=0)),
        ),
        *(
            LLMCase(name, available=_on_stub(adapter), unavailable=_on_closed_port(adapter))
            for name, adapter in http_adapters.items()
        ),
    ]


type TTSFactory = Callable[[], AbstractAsyncContextManager[TTSPort]]


@dataclass(frozen=True, slots=True)
class TTSCase:
    """Как получить адаптер TTSPort: рабочий и с недоступным движком.

    Реальный адаптер добавляется сюда, а если его модели нет на машине — пропускается
    (`pytest.param(..., marks=pytest.mark.skip(reason=...))`), фейк проверяется всегда.
    """

    name: str
    available: TTSFactory
    unavailable: TTSFactory


def tts_cases() -> list[TTSCase]:
    """Фейк в темпе целевого движка (RTF 0.3); реальные адаптеры — с S-7.3."""
    return [
        TTSCase(
            name="fake",
            available=lambda: nullcontext(FakeTTS(rtf=0.3, chunk_ms=200)),
            unavailable=lambda: nullcontext(FakeTTS(fail_after=0)),
        ),
    ]
