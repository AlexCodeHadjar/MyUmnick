"""FakeTTS: детерминированный «синтез» без модели и GPU, в заданном темпе (R-56)."""

import asyncio
import math
import sys
from array import array
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

from vtuber.domain import AudioChunk, AudioFormat, TTSUnavailable, VtuberError

MS_PER_S = 1000
TONE_HZ = 220.0
# Четверть полной шкалы: слышно и даёт ненулевую громкость для липсинка, но не клиппует.
TONE_AMPLITUDE = 0.25 * 32767


def tone_pcm(start: int, count: int, sample_rate: int) -> bytes:
    """PCM s16le синусоиды; `start` — номер первого сэмпла, чтобы фрагменты стыковались."""
    step = 2 * math.pi * TONE_HZ / sample_rate
    samples = array(
        "h", (round(TONE_AMPLITUDE * math.sin(step * n)) for n in range(start, start + count))
    )
    if sys.byteorder == "big":
        samples.byteswap()
    return samples.tobytes()


@dataclass(slots=True)
class FakeTTS:
    """Реализует TTSPort: фраза → тон по `ms_per_char` на символ, фрагментами по `chunk_ms`.

    `rtf` — темп синтеза: перед фрагментом длительностью d — пауза `rtf·d` (0 — мгновенно,
    0.3 — как целевой движок Этапа 7). `fail_after=N` — бросить `error_type` после N фрагментов
    (0 — движок недоступен сразу). Синтезированные фразы — в `phrases`.
    """

    sample_rate: int = 24_000
    rtf: float = 0.0
    ms_per_char: float = 60.0
    chunk_ms: float = 100.0
    fail_after: int | None = None
    error_type: type[VtuberError] = TTSUnavailable
    phrases: list[str] = field(default_factory=list)

    @property
    def audio_format(self) -> AudioFormat:
        return AudioFormat(self.sample_rate)

    async def synthesize(self, phrase: str) -> AsyncGenerator[AudioChunk]:
        self.phrases.append(phrase)
        if self.fail_after == 0:
            raise self._error()
        text = phrase.strip()
        total = round(len(text) * self.ms_per_char / MS_PER_S * self.sample_rate)
        per_chunk = max(1, round(self.chunk_ms / MS_PER_S * self.sample_rate))
        for index, start in enumerate(range(0, total, per_chunk)):
            if index == self.fail_after:
                raise self._error()
            count = min(per_chunk, total - start)
            # sleep(0) тоже уступает цикл: отмена срабатывает между фрагментами, как у движка.
            await asyncio.sleep(self.rtf * count / self.sample_rate)
            yield AudioChunk(self.audio_format, tone_pcm(start, count, self.sample_rate))

    def _error(self) -> VtuberError:
        return self.error_type(f"FakeTTS: отказ по сценарию теста (fail_after={self.fail_after})")
