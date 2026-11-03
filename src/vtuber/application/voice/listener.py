"""Голосовой ввод: кадры микрофона → детектор → фразы → распознавание → слушатель (Этап 11).

Окна обрабатываются по порядку в одной задаче; промежуточная гипотеза считается отдельной задачей и
только одна за раз: детектор не должен ждать Whisper. Переполненная очередь теряет старый звук,
а не задерживает новый. Сбой распознавания остаётся в логе: голос молчит, чат работает.
"""

import asyncio
import time
from collections import deque
from typing import TYPE_CHECKING, Final, NoReturn, Protocol

from pydantic import Field

from vtuber.application.voice.completeness import looks_unfinished
from vtuber.application.voice.segmenter import (
    BargeIn,
    Segmenter,
    SegmenterConfig,
    SegmentEvent,
    SpeechEnded,
    SpeechStarted,
)
from vtuber.domain import (
    SAMPLE_WIDTH_BYTES,
    AudioChunk,
    GenerationFailed,
    STTUnavailable,
)
from vtuber.kernel import ConfigSection, get_logger
from vtuber.ports import STTPort, VadPort

if TYPE_CHECKING:
    from collections.abc import Callable

MS_PER_S: Final = 1000
MAX_QUEUED_S: Final = 30

_log = get_logger(__name__)


class VoiceConfig(ConfigSection):
    """`interim_ms` — как часто считать промежуточную гипотезу; `min_phrase_ms` — короче не речь."""

    interim_ms: int = Field(gt=0)
    min_phrase_ms: int = Field(gt=0)
    segmenter: SegmenterConfig
    unfinished_hold_ms: int = Field(default=0, ge=0)  # S-14.2: 0 — ответ сразу после паузы


class VoiceEvents(Protocol):
    """Кто получает голосовой ввод: шлюз (шлёт в UI и начинает ход) или тест."""

    async def barge_in(self) -> None:
        """Пользователь заговорил: звук витюбера и текущий ход надо оборвать."""
        ...

    async def hypothesis(self, text: str) -> None:
        """Промежуточный текст фразы: показать и прогреть кэш LLM (T-05)."""
        ...

    async def final(self, text: str, ended_ns: int) -> None:
        """Фраза готова; `ended_ns` — конец речи по `clock`, для замера «конец речи → звук»."""
        ...


class VoiceListener:
    """Очередь кадров и обработка окон; `feed` не ждёт моделей, `run` — задачей у владельца."""

    def __init__(self, vad: VadPort, stt: STTPort, events: VoiceEvents, cfg: VoiceConfig) -> None:
        self._vad = vad
        self._stt = stt
        self._events = events
        self._cfg = cfg
        self._format = vad.audio_format
        self._window_bytes = vad.window_samples * SAMPLE_WIDTH_BYTES
        window_ms = vad.window_samples * MS_PER_S / self._format.sample_rate
        self._window_ms = window_ms
        self._segmenter = Segmenter(cfg.segmenter, window_ms)
        self._frames: deque[bytes] = deque(maxlen=round(MAX_QUEUED_S * MS_PER_S / window_ms))
        self._wake = asyncio.Event()
        self._buffer = bytearray()
        self._interim: asyncio.Task[None] | None = None
        self._since_interim_ms = 0.0
        self._held: str | None = None
        self._held_ended_ns = 0
        self._hold_timer: asyncio.Task[None] | None = None
        self.clock: Callable[[], int] = time.perf_counter_ns

    def feed(self, chunk: AudioChunk) -> None:
        """Кадр микрофона; режется на окна детектора. Другая частота — ошибка UI, кадр лишний."""
        if chunk.format != self._format:
            _log.warning("voice.bad_rate", rate=chunk.format.sample_rate)
            return
        self._buffer += chunk.pcm
        while len(self._buffer) >= self._window_bytes:
            self._frames.append(bytes(self._buffer[: self._window_bytes]))
            del self._buffer[: self._window_bytes]
        self._wake.set()

    async def run(self) -> NoReturn:
        """Обрабатывает окна по порядку; отмена снимает и промежуточную гипотезу."""
        try:
            while True:
                await self._wake.wait()
                self._wake.clear()
                while self._frames:
                    await self._process(self._frames.popleft())
        finally:
            self._stop_interim()
            self._stop_hold_timer()

    async def _process(self, window: bytes) -> None:
        probability = await self._vad.speech_probability(window)
        for event in self._segmenter.feed(window, probability):
            await self._handle(event)
        if self._segmenter.in_phrase:
            self._maybe_interim()

    async def _handle(self, event: SegmentEvent) -> None:
        if isinstance(event, SpeechStarted):
            self._since_interim_ms = 0.0
            self._stop_hold_timer()
        elif isinstance(event, BargeIn):
            await self._events.barge_in()
        elif isinstance(event, SpeechEnded):
            self._stop_interim()
            await self._finish(event)

    def _maybe_interim(self) -> None:
        self._since_interim_ms += self._window_ms
        busy = self._interim is not None and not self._interim.done()
        if busy or self._since_interim_ms < self._cfg.interim_ms:
            return
        self._since_interim_ms = 0.0
        self._interim = asyncio.create_task(self._send_interim(self._segmenter.phrase_pcm))

    async def _send_interim(self, pcm: bytes) -> None:
        try:
            text = await self._stt.transcribe(AudioChunk(self._format, pcm), final=False)
        except (STTUnavailable, GenerationFailed) as exc:
            _log.warning("voice.interim_failed", problem=str(exc))
            return
        if text:
            await self._events.hypothesis(text)

    def _stop_interim(self) -> None:
        if self._interim is not None and not self._interim.done():
            self._interim.cancel()
        self._interim = None

    async def _finish(self, ended: SpeechEnded) -> None:
        self._vad.reset()
        audio = AudioChunk(self._format, ended.pcm)
        if audio.duration_s * MS_PER_S < self._cfg.min_phrase_ms:
            await self._release_held()
            return
        # Конец речи — раньше этого момента на паузу конца фразы: её пользователь тоже ждёт.
        pause_ns = self._cfg.segmenter.end_silence_ms * 1_000_000
        ended_ns = self.clock() - pause_ns
        try:
            text = await self._stt.transcribe(audio, final=True)
        except (STTUnavailable, GenerationFailed) as exc:
            _log.warning("voice.final_failed", problem=str(exc))
            await self._release_held()
            return
        if not text:
            await self._release_held()
            return
        await self._deliver(text, ended_ns)

    async def _deliver(self, text: str, ended_ns: int) -> None:
        full = text if self._held is None else f"{self._held} {text}"
        self._held = None
        if self._cfg.unfinished_hold_ms > 0 and looks_unfinished(full):
            # Таймер, а не счёт окон: при push-to-talk кадры после фразы могут не прийти совсем.
            self._held = full
            self._held_ended_ns = ended_ns
            self._hold_timer = asyncio.create_task(self._hold_expires())
            return
        await self._events.final(full, ended_ns)

    async def _hold_expires(self) -> None:
        await asyncio.sleep(self._cfg.unfinished_hold_ms / MS_PER_S)
        await self._release_held()

    async def _release_held(self) -> None:
        held, self._held = self._held, None
        if held is not None:
            await self._events.final(held, self._held_ended_ns)

    def _stop_hold_timer(self) -> None:
        # Без удержанной фразы таймер уже отдаёт её в ход: такую передачу не обрывать.
        if self._held is not None and self._hold_timer is not None:
            self._hold_timer.cancel()
