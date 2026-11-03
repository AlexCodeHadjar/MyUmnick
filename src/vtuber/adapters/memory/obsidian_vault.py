"""Память в папке с Markdown для Obsidian (ADR-0020); само приложение Obsidian не нужно.

Заметка факта пишется атомарно, поэтому никто не увидит её наполовину. Чаты и дневник только
дописываются: так правка пользователя в том же файле не затирается целиком.
"""

import asyncio
import hashlib
import os
import threading
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path
from typing import Final

from vtuber.adapters.memory.note_format import (
    CHATS_DIR,
    DIARY_DIR,
    FACTS_DIR,
    HOST_NOTE,
    PEOPLE_DIR,
    SUMMARY_NOTE,
    BadNoteError,
    fact_note_name,
    parse_chat,
    parse_fact,
    render_diary_line,
    render_fact,
    render_host_note,
    render_turn,
)
from vtuber.domain import Fact, MemoryUnavailable, Turn, VaultScan
from vtuber.kernel import get_logger

NOTE_SUFFIX: Final = ".md"
_ENCODING: Final = "utf-8"

_log = get_logger(__name__)


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Точка в начале: Obsidian скрывает такие файлы и не покажет заметку в процессе записи.
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(text, encoding=_ENCODING, newline="\n")
    os.replace(temporary, path)  # noqa: PTH105 — внутри потока, важна атомарность замены


def _append(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding=_ENCODING, newline="\n") as file:
        file.write(text)


def _notes(folder: Path) -> Iterator[Path]:
    if folder.is_dir():
        yield from sorted(p for p in folder.rglob(f"*{NOTE_SUFFIX}") if not p.name.startswith("."))


class ObsidianVault:
    """MemoryVaultPort; файловые операции — в потоке (R-34), сбой — `MemoryUnavailable`."""

    def __init__(self, root: Path) -> None:
        self._root = root
        # Дозапись из нескольких потоков на Windows теряет строки (замер: 28 из 30).
        self._write_lock = threading.Lock()
        self._parsed: dict[str, tuple[tuple[int, int], Fact | None]] = {}

    async def save_fact(self, fact: Fact) -> Fact:
        """Новая заметка, строка в дневнике; возвращает факт с именем заметки."""
        return await self._in_thread(self._save_fact, fact)

    async def facts(self) -> list[Fact]:
        """Все разбираемые заметки фактов; битая — предупреждение, а не сбой всей памяти."""
        return list((await self.scan()).facts)

    async def scan(self) -> VaultScan:
        """Заметки: битая — предупреждение и имя в `broken`; её факт из индекса не пропадает."""
        return await self._in_thread(self._scan)

    async def changes_token(self) -> str:
        """Хеш имён, времён и размеров заметок фактов: файлы при этом не читаются."""
        return await self._in_thread(self._token)

    async def save_turn(self, turn: Turn, when: datetime) -> None:
        """Дописывает ход в заметку чата за этот день."""
        await self._in_thread(self._save_turn, turn, when)

    async def recent_turns(self, limit: int) -> list[Turn]:
        """Последние `limit` ходов по порядку, через границу дней."""
        return await self._in_thread(self._read_recent, limit)

    async def save_summary(self, summary: str) -> None:
        """Заменяет резюме разговора."""
        await self._in_thread(_write_atomic, self._summary_path(), summary.strip() + "\n")

    async def summary(self) -> str | None:
        """Резюме разговора; None — его ещё нет."""
        return await self._in_thread(self._read_summary)

    async def _in_thread[**P, R](
        self, call: Callable[P, R], *args: P.args, **kwargs: P.kwargs
    ) -> R:
        try:
            return await asyncio.to_thread(call, *args, **kwargs)
        except OSError as exc:
            msg = f"Папка памяти {self._root} недоступна: {exc}"
            raise MemoryUnavailable(msg) from exc

    def _save_fact(self, fact: Fact) -> Fact:
        name = fact_note_name(fact)
        saved = Fact(fact.text.strip(), fact.source, fact.importance, fact.created_at, note=name)
        target = self._root / FACTS_DIR / f"{name}{NOTE_SUFFIX}"
        with self._write_lock:
            if target.exists():
                # Факт уже записан и мог быть поправлен: правка пользователя главнее (S-16.5).
                return saved
            _write_atomic(target, render_fact(fact))
            host = self._root / PEOPLE_DIR / f"{HOST_NOTE}{NOTE_SUFFIX}"
            if not host.exists():
                _write_atomic(host, render_host_note())
            day = fact.created_at.astimezone().date().isoformat()
            _append(self._root / DIARY_DIR / f"{day}{NOTE_SUFFIX}", render_diary_line(name))
        return saved

    def _scan(self) -> VaultScan:
        parsed = {path.stem: self._parse_cached(path) for path in _notes(self._root / FACTS_DIR)}
        # Удалённые заметки из кэша убираются вместе с прошлым снимком.
        self._parsed = {note: self._parsed[note] for note in parsed}
        facts = tuple(fact for fact in parsed.values() if fact is not None)
        return VaultScan(facts, tuple(note for note, fact in parsed.items() if fact is None))

    def _parse_cached(self, path: Path) -> Fact | None:
        """Читает только изменённое: заметка стоит ~13 мс, а сверка идёт после каждого факта."""
        info = path.stat()
        stamp = (info.st_mtime_ns, info.st_size)
        cached = self._parsed.get(path.stem)
        if cached is not None and cached[0] == stamp:
            return cached[1]
        try:
            fact: Fact | None = parse_fact(path.read_text(encoding=_ENCODING), path.stem)
        except (BadNoteError, UnicodeDecodeError) as exc:
            _log.warning("vault.bad_note", note=path.name, problem=str(exc))
            fact = None
        self._parsed[path.stem] = (stamp, fact)
        return fact

    def _token(self) -> str:
        digest = hashlib.sha256()
        for path in _notes(self._root / FACTS_DIR):
            info = path.stat()
            digest.update(f"{path.name}|{info.st_mtime_ns}|{info.st_size}\n".encode())
        return digest.hexdigest()

    def _save_turn(self, turn: Turn, when: datetime) -> None:
        local = when.astimezone()
        path = self._root / CHATS_DIR / f"{local.date().isoformat()}{NOTE_SUFFIX}"
        with self._write_lock:
            _append(path, render_turn(turn, local))

    def _read_recent(self, limit: int) -> list[Turn]:
        days = [p for p in _notes(self._root / CHATS_DIR) if p.stem != SUMMARY_NOTE]
        turns: list[Turn] = []
        for path in reversed(days):
            turns = parse_chat(path.read_text(encoding=_ENCODING, errors="replace")) + turns
            if len(turns) >= limit:
                break
        return turns[-limit:] if limit else []

    def _summary_path(self) -> Path:
        return self._root / CHATS_DIR / f"{SUMMARY_NOTE}{NOTE_SUFFIX}"

    def _read_summary(self) -> str | None:
        path = self._summary_path()
        return (path.read_text(encoding=_ENCODING).strip() or None) if path.is_file() else None
