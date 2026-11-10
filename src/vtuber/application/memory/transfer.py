"""Перенос фактов о пользователе между изданиями (S-20.10, STAGE_20 раздел 2.4).

Каждое издание хранит память отдельно; перенос — через «входящие» другого издания: JSONL рядом с
его базой. Переводит только ядро, чья модель знает оба языка (русское; английская модель — только
английский), поэтому у русского ядра перевод включён и при выгрузке (ru → en), и при приёме
(en → ru); английское отдаёт и принимает как есть. Приватное и реплики зрителей в факты не попадают.
"""

import asyncio
import json
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final

from vtuber.application.memory.llm_text import collect
from vtuber.application.memory.vault_sync import reconcile
from vtuber.application.scheduler import IdleJob, IdleScheduler
from vtuber.domain import Fact, FactSource, GenerationFailed, Message, Role, VtuberError
from vtuber.kernel import get_logger
from vtuber.ports import EmbedderPort, GenerationParams, LLMPort, MemoryStorePort, MemoryVaultPort

INBOX_FILE: Final = "facts.jsonl"
DONE_SUFFIX: Final = ".done"
_PROMPTS: Final = {
    "en": "Translate each line into English. Keep the order and the number of lines. "
    "Reply with the translated lines only, one per line.",
    "ru": "Переведи каждую строку на русский. Сохрани порядок и число строк. "
    "Ответь только переведёнными строками, по одной на строку.",
}

_log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class TransferPaths:
    """Свои входящие и входящие другого издания (папка `inbox` рядом с базой памяти)."""

    own_inbox: Path
    other_inbox: Path
    own_language: str
    other_language: str


@dataclass(frozen=True, slots=True)
class MemoryParts:
    """Заметки (источник правды), индекс и эмбеддер: после приёма индекс сверяется (ADR-0020)."""

    vault: MemoryVaultPort
    store: MemoryStorePort
    embedder: EmbedderPort


class FactTransfer:
    """Выгрузить свои факты другому изданию и принять присланные им."""

    def __init__(
        self,
        paths: TransferPaths,
        memory: MemoryParts,
        translator: tuple[LLMPort, GenerationParams] | None,
    ) -> None:
        self._paths = paths
        self._memory = memory
        self._translator = translator

    async def export(self) -> int:
        """Все факты — во входящие другого издания (дописываются); возвращает, сколько.

        Raises:
            MemoryUnavailable: заметки недоступны.
            LLMUnavailable, GenerationFailed: перевод не удался.

        """
        facts = await self._memory.vault.facts()
        texts = await self._translated([fact.text for fact in facts], self._paths.other_language)
        rows = [
            {"text": text, "importance": fact.importance, "from": self._paths.own_language}
            for fact, text in zip(facts, texts, strict=True)
        ]
        # Файлы — в потоке: в корутине блокирующих вызовов нет.
        await asyncio.to_thread(_append_rows, self._paths.other_inbox, rows)
        _log.info("memory.transfer_exported", facts=len(rows), to=self._paths.other_language)
        return len(rows)

    async def import_inbox(self, when: datetime) -> int:
        """Присланные факты — в свои заметки; входящие помечаются принятыми, повторы пропускаются.

        Raises:
            MemoryUnavailable: заметки или индекс недоступны.
            LLMUnavailable, GenerationFailed: перевод не удался (входящие остаются на потом).

        """
        inbox = self._paths.own_inbox
        rows = await asyncio.to_thread(_read_rows, inbox)
        if not rows:
            return 0
        texts = await self._translated([text for text, _ in rows], self._paths.own_language)
        known = {fact.text.casefold() for fact in await self._memory.vault.facts()}
        added = 0
        for text, (_, importance) in zip(texts, rows, strict=True):
            if text.casefold() in known:
                continue
            await self._memory.vault.save_fact(Fact(text, FactSource.USER, importance, when))
            known.add(text.casefold())
            added += 1
        await reconcile(self._memory.vault, self._memory.store, self._memory.embedder)
        await asyncio.to_thread(inbox.replace, inbox.with_name(inbox.name + DONE_SUFFIX))
        _log.info("memory.transfer_imported", facts=added, received=len(rows))
        return added

    async def _translated(self, texts: Sequence[str], language: str) -> list[str]:
        if self._translator is None or not texts:
            return list(texts)
        llm, params = self._translator
        prompt = (Message(Role.SYSTEM, _PROMPTS[language]), Message(Role.USER, "\n".join(texts)))
        lines = [line.strip() for line in (await collect(llm, prompt, params)).splitlines()]
        lines = [line for line in lines if line]
        if len(lines) != len(texts):
            msg = f"перевод фактов: {len(lines)} строк вместо {len(texts)}"
            raise GenerationFailed(msg)
        return lines


def _append_rows(path: Path, rows: Sequence[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as file:
        file.writelines(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)


def _read_rows(path: Path) -> list[tuple[str, float]]:
    """Строки входящих (нет файла — пусто): битая строка пропускается, а не роняет приём."""
    if not path.is_file():
        return []
    rows: list[tuple[str, float]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            raw = json.loads(line)
            text, importance = str(raw["text"]).strip(), float(raw["importance"])
        except (ValueError, KeyError, TypeError):
            continue
        if text and 0 <= importance <= 1:
            rows.append((text, importance))
    return rows


type TransferDone = Callable[[int | None, str | None], Awaitable[None]]
"""Итог выгрузки для UI: сколько фактов, или текст ошибки."""


class TransferRequests:
    """Выгрузка по просьбе из UI — в простое (перевод занимает модель), итог — обратным вызовом."""

    def __init__(self, transfer: FactTransfer, scheduler: IdleScheduler) -> None:
        self._transfer = transfer
        self._scheduler = scheduler

    def request(self, done: TransferDone) -> None:
        """Поставить выгрузку в очередь простоя; ход её отменит и она повторится."""

        async def job() -> None:
            try:
                count = await self._transfer.export()
            except VtuberError as exc:
                await done(None, str(exc))
                return
            await done(count, None)

        self._scheduler.submit(IdleJob("memory:transfer_export", job))

    def import_on_start(self, when: datetime) -> None:
        """Принять присланное другим изданием в ближайшем простое (первая реплика не ждёт)."""

        async def job() -> None:
            try:
                await self._transfer.import_inbox(when)
            except VtuberError as exc:
                _log.warning("memory.transfer_import_failed", problem=str(exc))

        self._scheduler.submit(IdleJob("memory:transfer_import", job))
