"""Нарезка речи на фразы по вероятностям детектора: чистая логика, без моделей и времени.

Окна идут подряд, время считается по их длительности: так один и тот же звук режется одинаково,
как бы быстро он ни пришёл (push-to-talk присылает секунду тишины разом).
"""

from collections import deque
from dataclasses import dataclass

from pydantic import Field

from vtuber.kernel import ConfigSection


class SegmenterConfig(ConfigSection):
    """Подсекция `[stt.segmenter]`.

    `threshold` — вероятность речи; `start_ms` — столько речи подряд, чтобы считать её началом фразы
    (щелчок и кашель не считаются); `end_silence_ms` — пауза конца фразы; `barge_in_ms` — столько
    речи, чтобы перебить витюбера (Этап 11: ≥ 300 мс); `pre_roll_ms` — звук до начала речи, чтобы
    не съесть первый слог; `max_phrase_s` — длинная фраза закрывается принудительно.
    """

    threshold: float = Field(gt=0, lt=1)
    start_ms: int = Field(gt=0)
    end_silence_ms: int = Field(gt=0)
    barge_in_ms: int = Field(gt=0)
    pre_roll_ms: int = Field(ge=0)
    max_phrase_s: float = Field(gt=0)


@dataclass(frozen=True, slots=True)
class SpeechStarted:
    """Началась фраза."""


@dataclass(frozen=True, slots=True)
class BargeIn:
    """Речь длится достаточно, чтобы перебить витюбера; один раз на фразу."""


@dataclass(frozen=True, slots=True)
class SpeechEnded:
    """Фраза закончилась; `pcm` — вся фраза с паузой перед ней, без хвоста тишины."""

    pcm: bytes


type SegmentEvent = SpeechStarted | BargeIn | SpeechEnded


class Segmenter:
    """Состояние одной линии звука; `feed` принимает окна длиной `window_ms`."""

    def __init__(self, cfg: SegmenterConfig, window_ms: float) -> None:
        self._cfg = cfg
        self._window_ms = window_ms
        # Запас и на сами окна начала речи: фраза начинается раньше, чем её подтвердил `start_ms`.
        held_ms = cfg.pre_roll_ms + cfg.start_ms
        self._pre_roll: deque[bytes] = deque(maxlen=max(1, round(held_ms / window_ms)))
        self._phrase: list[bytes] = []
        self._voiced_ms = 0.0
        self._silent_ms = 0.0
        self._in_phrase = False
        self._barged = False

    @property
    def phrase_pcm(self) -> bytes:
        """Звук текущей фразы — для промежуточной гипотезы."""
        return b"".join(self._phrase)

    @property
    def in_phrase(self) -> bool:
        """Идёт ли фраза."""
        return self._in_phrase

    def feed(self, window: bytes, probability: float) -> list[SegmentEvent]:
        """Очередное окно и вероятность речи в нём; события — по порядку."""
        speech = probability >= self._cfg.threshold
        if self._in_phrase:
            return self._continue(window, speech=speech)
        return self._wait(window, speech=speech)

    def _wait(self, window: bytes, *, speech: bool) -> list[SegmentEvent]:
        self._pre_roll.append(window)
        self._voiced_ms = self._voiced_ms + self._window_ms if speech else 0.0
        if self._voiced_ms < self._cfg.start_ms:
            return []
        self._in_phrase = True
        self._silent_ms = 0.0
        self._barged = False
        self._phrase = list(self._pre_roll)
        self._pre_roll.clear()
        return [SpeechStarted(), *self._barge_if_long()]

    def _continue(self, window: bytes, *, speech: bool) -> list[SegmentEvent]:
        self._phrase.append(window)
        if speech:
            self._voiced_ms += self._window_ms
            self._silent_ms = 0.0
        else:
            self._silent_ms += self._window_ms
        too_long = len(self._phrase) * self._window_ms >= self._cfg.max_phrase_s * 1000
        if self._silent_ms >= self._cfg.end_silence_ms or too_long:
            return [self._finish()]
        return self._barge_if_long()

    def _barge_if_long(self) -> list[SegmentEvent]:
        if self._barged or self._voiced_ms < self._cfg.barge_in_ms:
            return []
        self._barged = True
        return [BargeIn()]

    def _finish(self) -> SpeechEnded:
        silent_windows = round(self._silent_ms / self._window_ms)
        kept = self._phrase[: len(self._phrase) - silent_windows]
        self._phrase = []
        self._in_phrase = False
        self._voiced_ms = 0.0
        return SpeechEnded(b"".join(kept))
