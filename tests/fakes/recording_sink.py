"""RecordingSink: записывает всё, что конвейер отдал получателю, с отметками времени."""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from vtuber.domain import AudioChunk, Emotion, Gesture

type Kind = Literal["text", "emotion", "gesture", "audio", "done"]


@dataclass(frozen=True, slots=True)
class Entry:
    """Одна запись: когда, что и с каким значением."""

    at_ns: int
    kind: Kind
    value: str | Emotion | Gesture | AudioChunk | None


@dataclass(slots=True)
class RecordingSink:
    """Реализует ReplySink; `clock` — `FakeClock` для управляемого времени."""

    clock: Callable[[], int] = time.perf_counter_ns
    entries: list[Entry] = field(default_factory=list)

    async def text(self, delta: str) -> None:
        self.entries.append(Entry(self.clock(), "text", delta))

    async def emotion(self, emotion: Emotion) -> None:
        self.entries.append(Entry(self.clock(), "emotion", emotion))

    async def gesture(self, gesture: Gesture) -> None:
        self.entries.append(Entry(self.clock(), "gesture", gesture))

    async def audio(self, chunk: AudioChunk) -> None:
        self.entries.append(Entry(self.clock(), "audio", chunk))

    async def done(self) -> None:
        self.entries.append(Entry(self.clock(), "done", None))

    def kinds(self) -> list[Kind]:
        return [entry.kind for entry in self.entries]

    def shown_text(self) -> str:
        return "".join(str(entry.value) for entry in self.entries if entry.kind == "text")

    def audio_chunks(self) -> list[AudioChunk]:
        return [entry.value for entry in self.entries if isinstance(entry.value, AudioChunk)]

    def emotions(self) -> list[Emotion]:
        return [entry.value for entry in self.entries if isinstance(entry.value, Emotion)]
