"""Плагин обмена блокнотом с карманным Умником (Этап 24, ADR-0050): сам находит телефон по USB."""

import asyncio
import contextlib
import json
from pathlib import Path
from typing import Final

from pydantic import Field

from vtuber.kernel import ConfigSection, PluginContext
from vtuber_phone_sync.drive import MtpDrive, PhoneDrive
from vtuber_phone_sync.merge import Note, fresh_from_phone, parse_jsonl, pc_payload

__all__ = ["MtpDrive", "Note", "PhoneDrive", "PhoneSyncConfig", "PhoneSyncPlugin"]

_RESYNC_EVERY: Final = 24  # опросов: пока кабель воткнут, заметки с телефона забираем раз в ~2 мин


class PhoneSyncConfig(ConfigSection):
    """Секция `[plugins.settings.phone_sync]`; `notes_file` — тот же, что у плагина tools."""

    notes_file: Path = Path("data/notes.txt")
    ledger_file: Path = Path("data/phone_sync.json")
    poll_s: float = Field(default=5.0, gt=0)


class PhoneSyncPlugin:
    """Фоновая задача: опрос MTP вне горячего пути; при подключении — забрать и отдать заметки."""

    name = "phone_sync"

    def __init__(self, drive: PhoneDrive | None = None) -> None:
        self._drive: PhoneDrive = drive or MtpDrive()
        self._ctx: PluginContext | None = None
        self._cfg = PhoneSyncConfig()
        self._task: asyncio.Task[None] | None = None

    async def setup(self, ctx: PluginContext) -> None:
        """Прочитать настройки и запустить опрос."""
        self._ctx = ctx
        self._cfg = ctx.settings(PhoneSyncConfig)
        self._task = asyncio.create_task(self._watch())

    async def shutdown(self) -> None:
        """Остановить опрос (CancelledError здесь ожидаем — R-правило: не глотаем чужую отмену)."""
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task

    async def _watch(self) -> None:
        polls = 0
        while True:
            phone = await self._drive.find()
            polls = polls + 1 if phone else 0
            if phone and polls % _RESYNC_EVERY == 1:
                await self.sync(phone)
            await asyncio.sleep(self._cfg.poll_s)

    async def sync(self, phone: str) -> int:
        """Один обмен; возвращает, сколько заметок пришло с телефона."""
        ledger = await asyncio.to_thread(_read_ledger, self._cfg.ledger_file)
        raw = await self._drive.pull_notes()
        fresh = fresh_from_phone(parse_jsonl(raw or ""), set(ledger))
        lines = await asyncio.to_thread(
            _append_and_read, self._cfg.notes_file, [n.text for n in fresh]
        )
        ledger.update({note.id: note.text for note in fresh})
        await asyncio.to_thread(_write_ledger, self._cfg.ledger_file, ledger)
        pushed = await self._drive.push_from_pc(pc_payload(lines, set(ledger.values())))
        if self._ctx is not None:
            self._ctx.log.info("phone_sync.done", phone=phone, received=len(fresh), pushed=pushed)
        return len(fresh)


def _read_ledger(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(key): str(value) for key, value in dict(data).items()}


def _write_ledger(path: Path, ledger: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8")


def _append_and_read(path: Path, texts: list[str]) -> list[str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.writelines(text.replace("\n", " ") + "\n" for text in texts)
    return path.read_text(encoding="utf-8").splitlines()
