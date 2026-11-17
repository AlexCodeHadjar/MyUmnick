"""Слияние блокнотов ПК и телефона (S-24.7, `docs/phone-sync.md`): чистые функции."""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class Note:
    """Заметка формата обмена: `id` уникален на обоих устройствах."""

    id: str
    text: str
    created: str
    origin: str


def parse_jsonl(raw: str) -> list[Note]:
    """Строки `notes.jsonl`; битые пропускаем: файл мог оборваться при отключении кабеля."""
    notes: list[Note] = []
    for line in raw.splitlines():
        try:
            item = json.loads(line)
            notes.append(Note(str(item["id"]), str(item["text"]), str(item["created"]), "phone"))
        except (ValueError, KeyError, TypeError):
            continue
    return notes


def fresh_from_phone(notes: list[Note], seen: set[str]) -> list[Note]:
    """Заметки телефона, которых ПК ещё не забирал; пустые не берём."""
    return [note for note in notes if note.id not in seen and note.text.strip()]


def pc_note_id(text: str) -> str:
    """Стабильный `id` строки `notes.txt`: одна и та же строка не уедет на телефон дважды."""
    return "pc-" + hashlib.sha1(text.encode("utf-8"), usedforsecurity=False).hexdigest()[:16]


def pc_payload(lines: list[str], from_phone: set[str]) -> str:
    """`from_pc.jsonl`: заметки ПК, кроме пришедших с телефона (они там уже есть)."""
    stamp = datetime.now(UTC).isoformat()
    rows = [
        json.dumps(
            {"id": pc_note_id(line), "text": line, "created": stamp, "origin": "pc"},
            ensure_ascii=False,
        )
        for line in lines
        if line.strip() and line not in from_phone
    ]
    return "".join(row + "\n" for row in rows)
