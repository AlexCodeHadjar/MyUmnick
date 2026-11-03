"""Разбор потока ответа LLM: теги эмоций и жестов → события, текст для чата, озвучки и истории."""

import re
from dataclasses import dataclass
from typing import Final

from vtuber.domain import TAG_CLOSE, TAG_OPEN, Emotion, Gesture, parse_gesture, parse_tag
from vtuber.ports import ReplySink

HOLD_LIMIT: Final = 32
"""Сколько символов после «<» ждать «>»: дальше это уже не тег, а текст (T-01: не задерживать)."""

_TAG_LIKE: Final = re.compile(r"<\s*/?\s*[A-Za-z_]+\s*>")
_TAG_PREFIX: Final = re.compile(r"<\s*/?\s*[A-Za-z_]*\s*")
_SPEECH_NOISE: Final = re.compile("[*_`#~\U0001f300-\U0001faff\u2600-\u27bf\ufe0f\u200d]")
_KNOWN_TAGS: Final = tuple(item.tag for item in (*Emotion, *Gesture))
GESTURE_GAP_CHARS: Final = 40
"""Сколько текста между жестами: модель, увлёкшись, не должна превращать фразу в дёргание."""


@dataclass(frozen=True, slots=True)
class TextDelta:
    """Порция текста: `text` — для чата, `spoken_text` — для TTS (без эмодзи и разметки)."""

    text: str
    spoken_text: str

    async def deliver(self, sink: ReplySink) -> None:
        """Отдаёт текст получателю."""
        await sink.text(self.text)


@dataclass(frozen=True, slots=True)
class EmotionCue:
    """В ответе встретился тег эмоции; озвучивать нечего."""

    emotion: Emotion
    spoken_text: str = ""

    async def deliver(self, sink: ReplySink) -> None:
        """Отдаёт смену эмоции получателю."""
        await sink.emotion(self.emotion)


@dataclass(frozen=True, slots=True)
class GestureCue:
    """В ответе встретился тег жеста; озвучивать нечего, речь он не задерживает."""

    gesture: Gesture
    spoken_text: str = ""

    async def deliver(self, sink: ReplySink) -> None:
        """Отдаёт жест получателю."""
        await sink.gesture(self.gesture)


type ParseEvent = TextDelta | EmotionCue | GestureCue


class StreamParser:
    """Разбирает дельты одного ответа по мере поступления (один экземпляр на ход).

    Тег — только `<слово>` или `</слово>` из латинских букв: модель закрывает и теги, которых не
    открывала (на замере 2026-11-03 в речь ушло `</thought>`); прочие «<» — обычный текст («3 < 5»).
    Буфер держится, лишь пока видно незакрытое «<», похожее на начало тега, и не дольше
    `HOLD_LIMIT` символов. Известные теги → `EmotionCue` и `GestureCue`, неизвестные выбрасываются.
    Жест не чаще, чем через `GESTURE_GAP_CHARS` символов: лишний выбрасывается и из истории.
    """

    def __init__(self) -> None:
        self._pending = ""
        self._full: list[str] = []
        self._since_gesture = GESTURE_GAP_CHARS

    @property
    def full_text(self) -> str:
        """Ответ для истории: текст и известные теги в нормализованном виде (`<happy>`)."""
        return "".join(self._full)

    def feed(self, delta: str) -> list[ParseEvent]:
        """События, которые уже можно отдать; хвост, похожий на начало тега, придерживается."""
        text, self._pending = self._pending + delta, ""
        events: list[ParseEvent] = []
        start = 0
        while (open_at := text.find(TAG_OPEN, start)) != -1:
            self._emit_text(text[start:open_at], events)
            start = self._consume_tag(text, open_at, events)
        self._emit_text(text[start:], events)
        return events

    def flush(self) -> list[ParseEvent]:
        """Конец ответа: недописанный известный тег (`<hap`) выбрасывается, остальное — текст."""
        pending, self._pending = self._pending, ""
        if _is_cut_known_tag(pending):
            return []
        events: list[ParseEvent] = []
        self._emit_text(pending, events)
        return events

    def _consume_tag(self, text: str, open_at: int, events: list[ParseEvent]) -> int:
        """Обрабатывает «<» в позиции `open_at`; возвращает, откуда продолжать разбор."""
        close_at = text.find(TAG_CLOSE, open_at)
        if close_at == -1:
            tail = text[open_at:]
            if len(tail) <= HOLD_LIMIT and _TAG_PREFIX.fullmatch(tail):
                self._pending = tail
                return len(text)
        elif _TAG_LIKE.fullmatch(candidate := text[open_at : close_at + 1]):
            self._apply_tag(candidate, events)
            return close_at + 1
        self._emit_text(TAG_OPEN, events)
        return open_at + 1

    def _apply_tag(self, tag: str, events: list[ParseEvent]) -> None:
        if emotion := parse_tag(tag):
            events.append(EmotionCue(emotion))
            self._full.append(emotion.tag)
        elif (gesture := parse_gesture(tag)) and self._since_gesture >= GESTURE_GAP_CHARS:
            self._since_gesture = 0
            events.append(GestureCue(gesture))
            self._full.append(gesture.tag)

    def _emit_text(self, text: str, events: list[ParseEvent]) -> None:
        if text:
            self._since_gesture += len(text)
            events.append(TextDelta(text, _SPEECH_NOISE.sub("", text)))
            self._full.append(text)


def _is_cut_known_tag(pending: str) -> bool:
    name = pending.removeprefix(TAG_OPEN).strip().lower()
    return bool(name) and any(tag.startswith(TAG_OPEN + name) for tag in _KNOWN_TAGS)
