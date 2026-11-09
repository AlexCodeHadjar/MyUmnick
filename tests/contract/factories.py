"""Адаптеры портов для контрактных тестов: каждый — в рабочем и в недоступном состоянии."""

import socket
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path

import httpx
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
from vtuber.adapters.tts.voice_server import VoiceServerConfig, VoiceServerTTS
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
        llamacpp=LlamaCppOptions(
            slot_id=0, enable_thinking=False, forbid_foreign_scripts=True, forbid_cyrillic=False
        ),
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
    long_phrase: str = (
        "Длинная фраза, чтобы синтез шёл заметное время и его можно было прервать. " * 3
    )


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
PIPER_VOICE_EN = ROOT / "models" / "tts" / "piper" / "en_US-ljspeech-medium.onnx"
KOKORO_DIR = ROOT / "models" / "tts" / "kokoro"
# Английским голосам — английская фраза: русскую их фонемизатор читает долго и по буквам.
LONG_PHRASE_EN = (
    "A long sentence, so that synthesis takes noticeable time and can be cut short. " * 3
)
KOKORO_MODEL = KOKORO_DIR / "kokoro-v1.0.onnx"


def _kokoro(model_path: Path) -> TTSFactory:
    @asynccontextmanager
    async def factory() -> AsyncIterator[TTSPort]:
        from vtuber.adapters.tts import KokoroConfig, KokoroTTS  # noqa: PLC0415

        cfg = KokoroConfig(
            model_path=model_path,
            voices_path=KOKORO_DIR / "voices-v1.0.bin",
            voice="af_heart",
            lang="en-us",
            speed=1.0,
            chunk_ms=200,
        )
        async with KokoroTTS(cfg) as tts:
            yield tts

    return factory


def _piper(model_path: Path) -> TTSFactory:
    @asynccontextmanager
    async def factory() -> AsyncIterator[TTSPort]:
        from vtuber.adapters.tts import PiperConfig, PiperTTS  # noqa: PLC0415

        cfg = PiperConfig(model_path=model_path, sample_rate=22050, length_scale=1.0, chunk_ms=200)
        async with PiperTTS(cfg) as tts:
            yield tts

    return factory


def _voice_server(*, reachable: bool) -> TTSFactory:
    """Настоящий адаптер и подменённый транспорт: движку нужен отдельный процесс (ADR-0031)."""

    def reply(request: httpx.Request) -> httpx.Response:
        if not reachable:
            raise httpx.ConnectError("no route", request=request)
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok", "sample_rate": 24000})
        return httpx.Response(200, content=b"\x01\x00" * 24000)

    @asynccontextmanager
    async def factory() -> AsyncIterator[TTSPort]:
        cfg = VoiceServerConfig(
            base_url="http://voice.test",
            connect_timeout_s=0.2,
            read_timeout_s=1,
            sample_rate=24000,
            chunk_ms=200,
        )
        async with VoiceServerTTS(
            cfg, transport=httpx.MockTransport(reply), check_pause_s=0
        ) as tts:
            yield tts

    return factory


def tts_cases() -> list[TTSCase]:
    """Фейк, Silero (ADR-0012), Piper (ADR-0013, ADR-0034), Kokoro (ADR-0034), сервер (ADR-0031)."""
    return [
        TTSCase(
            name="voice_server",
            available=_voice_server(reachable=True),
            unavailable=_voice_server(reachable=False),
        ),
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
        TTSCase(
            name="piper_en",
            available=_piper(PIPER_VOICE_EN),
            unavailable=_piper(PIPER_VOICE_EN.with_name("no-such-voice.onnx")),
            long_phrase=LONG_PHRASE_EN,
        ),
        TTSCase(
            name="kokoro",
            available=_kokoro(KOKORO_MODEL),
            unavailable=_kokoro(KOKORO_MODEL.with_name("no-such-model.onnx")),
            long_phrase=LONG_PHRASE_EN,
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
    no_piper_en = pytest.mark.skipif(
        not PIPER_VOICE_EN.is_file(), reason=f"нет голоса Piper {PIPER_VOICE_EN} (ADR-0034)"
    )
    no_kokoro = pytest.mark.skipif(
        not KOKORO_MODEL.is_file(), reason=f"нет модели Kokoro {KOKORO_MODEL} (ADR-0034)"
    )
    marks = {
        "silero": [pytest.mark.slow, no_silero],
        "piper": [pytest.mark.slow, no_piper],
        "piper_en": [pytest.mark.slow, no_piper_en],
        "kokoro": [pytest.mark.slow, no_kokoro],
    }
    return [
        pytest.param(case, id=case.name, marks=marks.get(case.name, ())) for case in tts_cases()
    ]
