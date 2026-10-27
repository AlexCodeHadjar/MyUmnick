"""Разбор потока ответа LLM: теги эмоций → события, текст для чата, озвучки и истории."""

import re
from dataclasses import dataclass
from typing import Final

from vtuber.domain import TAG_CLOSE, TAG_OPEN, Emotion, parse_tag
from vtuber.ports import ReplySink

HOLD_LIMIT: Final = 32
"""Сколько символов после «<» ждать «>»: дальше это уже не тег, а текст (T-01: не задерживать)."""

_TAG_LIKE: Final = re.compile(r"<\s*[A-Za-z_]+\s*>")
_TAG_PREFIX: Final = re.compile(r"<\s*[A-Za-z_]*\s*")
_SPEECH_NOISE: Final = re.compile("[*_`#~\U0001f300-\U0001faff\u2600-\u27bf\ufe0f\u200d]")
_KNOWN_TAGS: Final = tuple(emotion.tag for emotion in Emotion)


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


type ParseEvent = TextDelta | EmotionCue


class StreamParser:
    """Разбирает дельты одного ответа по мере поступления (один экземпляр на ход).

    Тег — только `<слово>` из латинских букв; прочие «<» — обычный текст («3 < 5»). Буфер
    держится, лишь пока видно незакрытое «<», похожее на начало тега, и не дольше
    `HOLD_LIMIT` символов. Известные теги → `EmotionCue`, неизвестные выбрасываются.
    """

    def __init__(self) -> None:
        self._pending = ""
        self._full: list[str] = []

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
            if emotion := parse_tag(candidate):
                events.append(EmotionCue(emotion))
                self._full.append(emotion.tag)
            return close_at + 1
        self._emit_text(TAG_OPEN, events)
        return open_at + 1

    def _emit_text(self, text: str, events: list[ParseEvent]) -> None:
        if text:
            events.append(TextDelta(text, _SPEECH_NOISE.sub("", text)))
            self._full.append(text)


def _is_cut_known_tag(pending: str) -> bool:
    name = pending.removeprefix(TAG_OPEN).strip().lower()
    return bool(name) and any(tag.startswith(TAG_OPEN + name) for tag in _KNOWN_TAGS)
