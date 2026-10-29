"""Междометия-заглушки (T-17): «Хм…», «Так…» — если звук ответа не готов к сроку.

Синтезируются один раз при загрузке голоса: в ходе отдаются готовые фрагменты, синтез заглушки
не конкурирует за CPU с настоящей фразой. Заглушка и ответ не накладываются: звук хода пишет
один `AudioOut`, и заглушка звучит, только если ответ ещё не начал звучать; начавшаяся
заглушка доигрывается целиком, ответ встаёт за ней.
"""

import asyncio
from collections.abc import Sequence
from contextlib import aclosing

from pydantic import Field

from vtuber.application.speech import normalize_for_speech
from vtuber.domain import AudioChunk
from vtuber.kernel import ConfigSection
from vtuber.ports import ReplySink, TTSPort

MS_PER_S = 1000

type Clip = tuple[AudioChunk, ...]
"""Звук одного междометия."""


class FillerConfig(ConfigSection):
    """Секция `[pipeline.filler]`.

    `after_ms` — сколько ждать звука ответа от начала хода, прежде чем сказать междометие;
    `phrases` — междометия, звучат по очереди.
    """

    enabled: bool
    after_ms: int = Field(gt=0)
    phrases: tuple[str, ...]


class FillerBank:
    """Готовые к отдаче междометия; пустой банк (голос не загружен, выключено) — молчит."""

    def __init__(self, cfg: FillerConfig) -> None:
        self._cfg = cfg
        self._clips: list[Clip] = []
        self._next = 0

    @property
    def after_s(self) -> float:
        """Срок звука ответа, секунд от начала хода."""
        return self._cfg.after_ms / MS_PER_S

    @property
    def ready(self) -> bool:
        """Есть что сказать."""
        return bool(self._clips)

    async def prepare(self, tts: TTSPort) -> None:
        """Синтезирует междометия; ошибки движка — наружу (вызывающий решает, жить ли без них).

        Raises:
            TTSUnavailable: движок не загружен.
            GenerationFailed: синтез сорвался.

        """
        if not self._cfg.enabled:
            return
        clips = [await _synthesize(tts, phrase) for phrase in self._cfg.phrases]
        self._clips = [clip for clip in clips if clip]

    def next_clip(self) -> Clip:
        """Следующее междометие по кругу: одно и то же подряд звучит механически."""
        clip = self._clips[self._next % len(self._clips)]
        self._next += 1
        return clip


class AudioOut:
    """Единственный писатель звука хода: ответ и междометие не перемешиваются."""

    def __init__(self, sink: ReplySink) -> None:
        self._sink = sink
        self._lock = asyncio.Lock()
        self._answered = False

    async def answer(self, chunk: AudioChunk) -> None:
        """Фрагмент ответа; идущее междометие сначала доигрывается."""
        async with self._lock:
            self._answered = True
            await self._sink.audio(chunk)

    async def filler(self, clip: Sequence[AudioChunk]) -> bool:
        """Междометие целиком, если ответ ещё не звучит; True — сказано."""
        async with self._lock:
            if self._answered:
                return False
            for chunk in clip:
                await self._sink.audio(chunk)
            return True


async def _synthesize(tts: TTSPort, phrase: str) -> Clip:
    async with aclosing(tts.synthesize(normalize_for_speech(phrase))) as audio:
        return tuple([chunk async for chunk in audio])
