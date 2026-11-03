"""Кто говорит (S-14.3, ADR-0029): отпечаток голоса на каждую фразу, метка в реплике.

Фразы уже нарезаны детектором речи, поэтому отдельная разметка «кто когда» не нужна. Отпечаток
считается рядом с Whisper и быстрее него, ответ его не ждёт. Отпечатки только в памяти: при
перезапуске номера начинаются заново. Пока слышен один человек, метки нет и реплика такая же,
как раньше.
"""

import asyncio
import math
from collections.abc import Sequence
from typing import Final

from pydantic import Field

from vtuber.domain import AudioChunk, GenerationFailed, STTUnavailable
from vtuber.kernel import ConfigSection, get_logger
from vtuber.ports import SpeakerEmbedderPort

_log = get_logger(__name__)
SPEAKER_WORD: Final = "Собеседник"


class SpeakersConfig(ConfigSection):
    """Секция `[stt.speakers]`: порог сходства подобран на синтетике, на людях не проверен."""

    enabled: bool
    threshold: float = Field(gt=0, lt=1)
    min_phrase_s: float = Field(ge=0)
    max_speakers: int = Field(ge=2)
    wait_s: float = Field(gt=0)


def _normalized(vector: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [x / norm for x in vector]


def _similarity(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


class SpeakerTracker:
    """Голоса разговора: близкий отпечаток уточняет знакомый голос, далёкий заводит новый."""

    def __init__(self, threshold: float, max_speakers: int) -> None:
        self._threshold = threshold
        self._max_speakers = max_speakers
        self._centers: list[list[float]] = []
        self._counts: list[int] = []

    @property
    def count(self) -> int:
        """Сколько голосов уже слышно."""
        return len(self._centers)

    def identify(self, vector: Sequence[float]) -> int:
        """Номер голоса с 1; мест больше нет — ближайший из известных."""
        unit = _normalized(vector)
        scores = [_similarity(unit, center) for center in self._centers]
        best = max(range(len(scores)), key=scores.__getitem__, default=-1)
        room = len(self._centers) < self._max_speakers
        if best < 0 or (room and scores[best] < self._threshold):
            self._centers.append(unit)
            self._counts.append(1)
            return len(self._centers)
        self._absorb(best, unit)
        return best + 1

    def _absorb(self, index: int, unit: Sequence[float]) -> None:
        count = self._counts[index]
        merged = [
            (c * count + u) / (count + 1) for c, u in zip(self._centers[index], unit, strict=True)
        ]
        self._centers[index] = _normalized(merged)
        self._counts[index] = count + 1


class SpeakerLabeler:
    """Метка фразы или None: один голос, короткая фраза, сбой. Без метки реплика идёт как есть."""

    def __init__(self, cfg: SpeakersConfig, embedder: SpeakerEmbedderPort) -> None:
        self._cfg = cfg
        self._embedder = embedder
        self._tracker = SpeakerTracker(cfg.threshold, cfg.max_speakers)

    async def label(self, audio: AudioChunk) -> str | None:
        """На короткой фразе отпечаток ненадёжен: лучше без метки, чем с чужой."""
        if audio.duration_s < self._cfg.min_phrase_s:
            return None
        try:
            vector = await self._embedder.embed(audio)
        except (STTUnavailable, GenerationFailed) as exc:
            _log.warning("speakers.failed", problem=str(exc))
            return None
        number = self._tracker.identify(vector)
        return f"{SPEAKER_WORD} {number}" if self._tracker.count > 1 else None

    async def label_in_time(self, task: "asyncio.Task[str | None]") -> str | None:
        """Whisper уже закончил: ждать отпечаток можно лишь чуть-чуть, ответ важнее метки."""
        done, _ = await asyncio.wait({task}, timeout=self._cfg.wait_s)
        if not done:
            task.cancel()
            return None
        return task.result()


def labelled(text: str, label: str | None) -> str:
    """Реплика с меткой говорящего: так она попадает и к модели, и в историю."""
    return text if label is None else f"{label}: {text}"
