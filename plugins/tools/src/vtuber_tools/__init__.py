"""Плагин инструментов: время, таймер, заметки — до LLM, одна генерация вместо двух (S-12.4)."""

import asyncio
from collections.abc import AsyncGenerator, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from pydantic import Field

from vtuber.domain import IncomingMessage
from vtuber.kernel import ConfigSection, PluginContext
from vtuber_tools.intents import (
    AddNote,
    AskTime,
    Intent,
    ListNotes,
    SetTimer,
    detect_intent,
)

__all__ = [
    "AddNote",
    "AskTime",
    "ListNotes",
    "SetTimer",
    "ToolsConfig",
    "ToolsPlugin",
    "detect_intent",
]

_WEEKDAYS: Final = (
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "воскресенье",
)
_MONTHS: Final = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)
_SOURCE: Final = "timer"
_SECONDS_IN_MINUTE: Final = 60


class ToolsConfig(ConfigSection):
    """Секция `[plugins.settings.tools]`."""

    notes_file: Path = Path("data/notes.txt")
    max_notes_read: int = Field(default=10, ge=1)


def describe_seconds(seconds: int) -> str:
    """Длительность для справки модели: она сама просклоняет, цифры ей понятнее слов."""
    if seconds < _SECONDS_IN_MINUTE:
        return f"{seconds} сек"
    return f"{seconds // _SECONDS_IN_MINUTE} мин"


class ToolsPlugin:
    """Выполняет просьбу до запроса к LLM и кладёт результат в справку хода."""

    name = "tools"

    def __init__(
        self, now: Callable[[], datetime] = lambda: datetime.now(UTC).astimezone()
    ) -> None:
        self._now = now
        self._cfg: ToolsConfig | None = None
        self._timers: set[asyncio.Task[None]] = set()
        self._fired: asyncio.Queue[IncomingMessage] = asyncio.Queue()

    async def setup(self, ctx: PluginContext) -> None:
        """Подключить справку хода и источник сработавших таймеров."""
        self._cfg = ctx.settings(ToolsConfig)
        ctx.add_context(self.context)
        ctx.add_source(self.fired)

    async def shutdown(self) -> None:
        """Несработавшие таймеры пропадают: в файле они не хранятся."""
        for timer in tuple(self._timers):
            timer.cancel()

    async def context(self, text: str) -> str | None:
        """Результат инструмента для справки; None — реплика не про инструменты."""
        intent = detect_intent(text)
        return None if intent is None else await self._run(intent)

    async def fired(self) -> AsyncGenerator[IncomingMessage]:
        """Сработавшие таймеры: витюбер скажет о них, когда договорит."""
        while True:
            yield await self._fired.get()

    async def _run(self, intent: Intent) -> str:
        match intent:
            case AskTime():
                return self._time_now()
            case SetTimer():
                return self._set_timer(intent)
            case AddNote():
                await asyncio.to_thread(self._append_note, intent.text)
                return f"Заметка записана: {intent.text}."
            case ListNotes():
                notes = await asyncio.to_thread(self._read_notes)
                return f"Заметки: {'; '.join(notes)}." if notes else "Заметок пока нет."

    def _time_now(self) -> str:
        now = self._now()
        date = f"{now.day} {_MONTHS[now.month - 1]} {now.year}"
        return f"Сейчас {now:%H:%M}, {_WEEKDAYS[now.weekday()]}, {date}."

    def _set_timer(self, intent: SetTimer) -> str:
        timer = asyncio.create_task(self._ring(intent))
        self._timers.add(timer)
        timer.add_done_callback(self._timers.discard)
        about = f" ({intent.about})" if intent.about else ""
        return f"Таймер на {describe_seconds(intent.seconds)}{about} поставлен и уже идёт."

    async def _ring(self, intent: SetTimer) -> None:
        await asyncio.sleep(intent.seconds)
        about = f": {intent.about}" if intent.about else ""
        text = f"сработал таймер на {describe_seconds(intent.seconds)}{about}"
        self._fired.put_nowait(IncomingMessage(_SOURCE, "Таймер", text, is_viewer=False))

    def _notes_path(self) -> Path:
        if self._cfg is None:
            msg = "Плагин tools не запущен"
            raise RuntimeError(msg)
        return self._cfg.notes_file

    def _append_note(self, text: str) -> None:
        path = self._notes_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            file.write(text.replace("\n", " ") + "\n")

    def _read_notes(self) -> list[str]:
        path = self._notes_path()
        if not path.is_file() or self._cfg is None:
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        return lines[-self._cfg.max_notes_read :]
