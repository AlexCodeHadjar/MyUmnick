"""Адаптеры портов для контрактных тестов: каждый — в рабочем и в недоступном состоянии."""

import socket
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path

import pytest

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
        llamacpp=LlamaCppOptions(slot_id=0, enable_thinking=False, forbid_foreign_scripts=True),
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


ROOT = Path(__file__).resolve().parents[2]
SILERO_MODEL = ROOT / "models" / "tts" / "silero" / "v5_6_ru.pt"


def _silero(model_path: Path) -> TTSFactory:
    @asynccontextmanager
    async def factory() -> AsyncIterator[TTSPort]:
        # torch грузится только при запуске случая: быстрый прогон тестов его не ждёт.
        from vtuber.adapters.tts import SileroConfig, SileroTTS  # noqa: PLC0415

        cfg = SileroConfig(
            model_path=model_path, speaker="xenia", sample_rate=24000, threads=4, chunk_ms=200
        )
        async with SileroTTS(cfg) as tts:
            yield tts

    return factory


PIPER_VOICE = ROOT / "models" / "tts" / "piper" / "ru_RU-denis-medium.onnx"


def _piper(model_path: Path) -> TTSFactory:
    @asynccontextmanager
    async def factory() -> AsyncIterator[TTSPort]:
        from vtuber.adapters.tts import PiperConfig, PiperTTS  # noqa: PLC0415

        cfg = PiperConfig(model_path=model_path, sample_rate=22050, length_scale=1.0, chunk_ms=200)
        async with PiperTTS(cfg) as tts:
            yield tts

    return factory


def tts_cases() -> list[TTSCase]:
    """Фейк в темпе целевого движка (RTF 0.3), Silero (ADR-0012) и Piper (ADR-0013)."""
    return [
        TTSCase(
            name="fake",
            available=lambda: nullcontext(FakeTTS(rtf=0.3, chunk_ms=200)),
            unavailable=lambda: nullcontext(FakeTTS(fail_after=0)),
        ),
        TTSCase(
            name="silero",
            available=_silero(SILERO_MODEL),
            unavailable=_silero(SILERO_MODEL.with_name("нет-такой-модели.pt")),
        ),
        TTSCase(
            name="piper",
            available=_piper(PIPER_VOICE),
            unavailable=_piper(PIPER_VOICE.with_name("нет-такого-голоса.onnx")),
        ),
    ]


def tts_params() -> list[object]:
    """Случаи для `pytest` с метками: Silero — медленный (грузит модель) и требует её файл."""
    no_silero = pytest.mark.skipif(
        not SILERO_MODEL.is_file(), reason=f"нет модели Silero {SILERO_MODEL} (ADR-0012)"
    )
    no_piper = pytest.mark.skipif(
        not PIPER_VOICE.is_file(), reason=f"нет голоса Piper {PIPER_VOICE} (ADR-0013)"
    )
    marks = {"silero": [pytest.mark.slow, no_silero], "piper": [pytest.mark.slow, no_piper]}
    return [
        pytest.param(case, id=case.name, marks=marks.get(case.name, ())) for case in tts_cases()
    ]
