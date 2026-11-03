"""Звуки вокруг (S-14.4): смех, аплодисменты и другое становятся событиями шины и редкой реакцией.

Идёт мимо `VoiceListener`: детектор пропускает только речь, аплодисментов и музыки он не увидит.
Звук лежит только в памяти и только одно окно. Выключено — объекта нет, цены для диалога нет.
"""

import array
import asyncio
import math
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, NoReturn

from pydantic import Field

from vtuber.domain import (
    SAMPLE_WIDTH_BYTES,
    AudioChunk,
    GenerationFailed,
    SoundHeard,
    SoundKind,
    STTUnavailable,
)
from vtuber.kernel import ConfigSection, EventBus, get_logger
from vtuber.ports import SoundClassifierPort

_log = get_logger(__name__)
_FULL_SCALE: Final = 32768.0

REACTIONS: Final[Mapping[SoundKind, str]] = MappingProxyType(
    {
        SoundKind.LAUGHTER: "(Рядом смеются. Отреагируй одной короткой фразой.)",
        SoundKind.APPLAUSE: "(Рядом аплодируют. Отреагируй одной короткой фразой.)",
        SoundKind.COUGH: "(Ведущий кашлянул. Коротко и по-доброму отреагируй.)",
        SoundKind.SNEEZE: "(Ведущий чихнул. Коротко пожелай здоровья.)",
        SoundKind.CRY: "(Кажется, рядом плачут. Коротко и осторожно спроси, всё ли хорошо.)",
        SoundKind.MUSIC: "(Рядом играет музыка. Отреагируй одной короткой фразой.)",
    }
)


class SoundsConfig(ConfigSection):
    """Секция `[stt.sounds]`: выключена, пока не проверена точность на настоящих записях."""

    enabled: bool
    window_s: float = Field(gt=0)
    gate_rms: float = Field(ge=0, lt=1)
    min_gap_s: float = Field(gt=0)
    react_to: tuple[SoundKind, ...]


@dataclass(frozen=True, slots=True)
class SoundActions:
    """`busy` — идёт ход, речь или фраза ведущего; `react` — сказать реплику в тишине."""

    react: Callable[[str], Awaitable[None]]
    busy: Callable[[], bool]


def loudness(pcm: bytes) -> float:
    """Громкость окна s16le, 0…1: на тишину модель не тратится."""
    samples = array.array("h", pcm[: len(pcm) - len(pcm) % SAMPLE_WIDTH_BYTES])
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples)) / _FULL_SCALE


class SoundWatcher:
    """Собирает окна и разбирает только последнее: отставшая разметка никому не нужна."""

    def __init__(
        self,
        cfg: SoundsConfig,
        classifier: SoundClassifierPort,
        bus: EventBus,
        actions: SoundActions,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._cfg = cfg
        self._classifier = classifier
        self._bus = bus
        self._actions = actions
        self._clock = clock
        self._collecting = bytearray()
        self._ready: AudioChunk | None = None
        self._wake = asyncio.Event()
        self._reacted_at: float | None = None

    def feed(self, chunk: AudioChunk) -> None:
        """Кадр микрофона; не ждёт модель и ничего не копит сверх окна."""
        self._collecting += chunk.pcm
        window = round(self._cfg.window_s * chunk.format.bytes_per_second)
        if len(self._collecting) >= window:
            self._ready = AudioChunk(chunk.format, bytes(self._collecting))
            self._collecting.clear()
            self._wake.set()

    async def run(self) -> NoReturn:
        """Цикл на всё время работы; владелец — bootstrap."""
        while True:
            await self._wake.wait()
            self._wake.clear()
            audio, self._ready = self._ready, None
            if audio is not None:
                await self._examine(audio)

    async def _examine(self, audio: AudioChunk) -> None:
        if self._actions.busy() or loudness(audio.pcm) < self._cfg.gate_rms:
            return
        try:
            kind = await self._classifier.classify(audio)
        except (STTUnavailable, GenerationFailed) as exc:
            _log.warning("sounds.failed", problem=str(exc))
            return
        if kind is not None:
            await self._bus.publish(SoundHeard(kind))
            await self._maybe_react(kind)

    async def _maybe_react(self, kind: SoundKind) -> None:
        # Занятость ещё раз: разбор идёт дольше кадра, ведущий мог заговорить (не перебивать его).
        if kind not in self._cfg.react_to or self._actions.busy() or not self._gap_passed():
            return
        self._reacted_at = self._clock()
        await self._actions.react(REACTIONS[kind])

    def _gap_passed(self) -> bool:
        last = self._reacted_at
        return last is None or self._clock() - last >= self._cfg.min_gap_s
