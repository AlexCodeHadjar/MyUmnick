"""Piper TTS (ADR-0013): голос ONNX на CPU через `piper-tts`, синтез фразы в потоке."""

import asyncio
import threading
from collections.abc import AsyncGenerator, Callable, Iterable
from pathlib import Path
from types import TracebackType
from typing import Protocol, Self

from pydantic import Field

from vtuber.domain import (
    SAMPLE_WIDTH_BYTES,
    AudioChunk,
    AudioFormat,
    GenerationFailed,
    TTSUnavailable,
)
from vtuber.kernel import ConfigSection

MS_PER_S = 1000
# Первый синтез ONNX Runtime готовит граф ~1.5 с — платим при загрузке, а не на первой реплике
# (T-06).
WARMUP_PHRASE = "Привет."
VOICE_URL = "https://huggingface.co/rhasspy/piper-voices/tree/main/ru/ru_RU/denis/medium"


class PiperConfig(ConfigSection):
    """Подсекция `[tts.piper]`.

    `sample_rate` — частота голоса из его `.onnx.json` (у medium — 22050): объявлена в конфиге,
    чтобы формат был известен до загрузки, и сверяется с голосом при загрузке.
    `length_scale` — темп речи (1 — как обучен голос, больше — медленнее).
    """

    model_path: Path
    sample_rate: int = Field(gt=0)
    length_scale: float = Field(gt=0)
    chunk_ms: int = Field(gt=0)


class PiperChunk(Protocol):
    """Фрагмент `piper.AudioChunk`: PCM s16le моно."""

    @property
    def audio_int16_bytes(self) -> bytes:
        """PCM фрагмента."""
        ...


class PiperVoiceLike(Protocol):
    """То, что нужно от `piper.PiperVoice`: частота голоса и синтез по предложениям."""

    @property
    def sample_rate(self) -> int:
        """Частота PCM голоса."""
        ...

    def synthesize_chunks(self, text: str, length_scale: float) -> Iterable[PiperChunk]:
        """Фрагменты фразы по предложениям."""
        ...


type VoiceLoader = Callable[[Path], PiperVoiceLike]


class _LoadedVoice:
    """Обёртка над `PiperVoice`: узкий интерфейс вместо всего API пакета."""

    def __init__(self, path: Path) -> None:
        from piper import PiperVoice  # noqa: PLC0415 — пакет из группы `piper`, грузится по делу

        self._voice = PiperVoice.load(path)

    @property
    def sample_rate(self) -> int:
        return self._voice.config.sample_rate

    def synthesize_chunks(self, text: str, length_scale: float) -> Iterable[PiperChunk]:
        from piper import SynthesisConfig  # noqa: PLC0415

        return self._voice.synthesize(text, SynthesisConfig(length_scale=length_scale))


def load_voice(path: Path) -> PiperVoiceLike:
    """Голос Piper: `.onnx` и рядом `.onnx.json`."""
    if not path.is_file():
        raise FileNotFoundError(path)
    return _LoadedVoice(path)


class PiperTTS:
    """Реализует TTSPort; голос грузится и прогревается один раз в `async with` (R-40).

    Голоса нет или он не читается — старт не падает, синтез отвечает `TTSUnavailable`.
    """

    def __init__(self, cfg: PiperConfig, loader: VoiceLoader = load_voice) -> None:
        self._cfg = cfg
        self._loader = loader
        self._voice: PiperVoiceLike | None = None
        self._unavailable = "Piper не загружен: адаптер используется вне `async with`"
        # Отменённый синтез дорабатывает в своём потоке — следующий ждёт его, а не мешает.
        self._lock = threading.Lock()

    async def __aenter__(self) -> Self:
        try:
            self._voice = await asyncio.to_thread(self._load)
        except FileNotFoundError:
            self._unavailable = (
                f"Нет голоса Piper {self._cfg.model_path}: "
                f"скачайте .onnx и .onnx.json с {VOICE_URL}"
            )
        # onnxruntime бросает свои pybind-исключения — любое из них значит «голос не готов» (R-43).
        except Exception as error:  # noqa: BLE001
            self._unavailable = f"Голос Piper не загрузился ({self._cfg.model_path}): {error}"
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._voice = None

    @property
    def audio_format(self) -> AudioFormat:
        """PCM s16le с частотой голоса из конфига."""
        return AudioFormat(self._cfg.sample_rate)

    async def synthesize(self, phrase: str) -> AsyncGenerator[AudioChunk]:
        """Фраза синтезируется в потоке и уходит фрагментами по `chunk_ms`."""
        voice = self._voice
        if voice is None:
            raise TTSUnavailable(self._unavailable)
        text = phrase.strip()
        # Без букв говорить нечего («…», «—»): тишина, а не странный звук фонемизатора.
        if not any(char.isalpha() for char in text):
            return
        pcm = await asyncio.to_thread(self._synthesize_pcm, voice, text)
        step = self._chunk_bytes()
        for start in range(0, len(pcm), step):
            yield AudioChunk(self.audio_format, pcm[start : start + step])
            # Уступка цикла: отмена срабатывает между фрагментами (T-14, контракт TTSPort).
            await asyncio.sleep(0)

    def _load(self) -> PiperVoiceLike:
        voice = self._loader(self._cfg.model_path)
        if voice.sample_rate != self._cfg.sample_rate:
            msg = (
                f"частота голоса {voice.sample_rate} Гц, а в конфиге {self._cfg.sample_rate} — "
                "исправьте `[tts.piper] sample_rate`"
            )
            raise ValueError(msg)
        self._synthesize_pcm(voice, WARMUP_PHRASE)
        return voice

    def _synthesize_pcm(self, voice: PiperVoiceLike, text: str) -> bytes:
        with self._lock:
            try:
                chunks = voice.synthesize_chunks(text, self._cfg.length_scale)
                return b"".join(chunk.audio_int16_bytes for chunk in chunks)
            # Любое исключение onnxruntime или фонемизатора — доменная ошибка (R-43).
            except Exception as error:
                msg = f"Piper не синтезировал фразу «{text[:40]}»: {error}"
                raise GenerationFailed(msg) from error

    def _chunk_bytes(self) -> int:
        samples = max(1, self._cfg.sample_rate * self._cfg.chunk_ms // MS_PER_S)
        return samples * SAMPLE_WIDTH_BYTES
