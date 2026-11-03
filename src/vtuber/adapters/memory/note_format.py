"""Заметки хранилища Obsidian как текст (ADR-0020): без диска, поэтому проверяется просто.

Свойства в начале файла — плоский YAML: строки в JSON-кавычках для этого подмножество YAML, значит
Obsidian их читает, а библиотека не нужна. Пользователь и Obsidian могут переписать значения
по-своему, поэтому чтение терпимо к кавычкам и лишним свойствам; непонятная заметка — ошибка только
для неё.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from vtuber.domain import Fact, FactSource, Turn, TurnId

FACTS_DIR: Final = "Факты"
CHATS_DIR: Final = "Чаты"
DIARY_DIR: Final = "Дневник"
PEOPLE_DIR: Final = "Люди"
HOST_NOTE: Final = "Ведущий"
SUMMARY_NOTE: Final = "Резюме"

_FOOTER_LABEL: Final = "Связано:"
_USER_LABEL: Final = "**Ты:** "
_REPLY_LABEL: Final = "**Витюбер:** "
_INTERRUPTED: Final = "прервано"
_EXTERNAL: Final = "не ведущий"
_SLUG_CHARS: Final = 40
_NOT_IN_FILE_NAME: Final = re.compile(r'[\\/:*?"<>|#^\[\]\s.]+')
_PROPERTIES: Final = re.compile(r"\A---\n(?P<props>.*?)\n---\n?", re.DOTALL)
_TURN_HEADING: Final = re.compile(
    r"^## (?P<time>\d\d:\d\d:\d\d)(?: \((?P<flags>[^)]*)\))?$", re.MULTILINE
)
_NEEDS_ESCAPE: Final = re.compile(r"^(?=## |\*\*Ты:\*\* |\*\*Витюбер:\*\* |\\)", re.MULTILINE)
_ESCAPED: Final = re.compile(r"^\\", re.MULTILINE)


class BadNoteError(ValueError):
    """Заметку не удалось разобрать; остальная память от этого не страдает."""


def fact_note_name(fact: Fact) -> str:
    """Имя файла без расширения: читаемое начало текста и метка, чтобы имена не совпадали."""
    slug = _NOT_IN_FILE_NAME.sub(" ", fact.text).strip()[:_SLUG_CHARS].strip() or "факт"
    identity = f"{fact.text}|{fact.created_at.isoformat()}".encode()
    return f"{slug} {hashlib.sha256(identity).hexdigest()[:6]}"


def render_fact(fact: Fact) -> str:
    """Заметка факта; ссылки дают связи в графе Obsidian."""
    day = fact.created_at.astimezone().date().isoformat()
    links = f"[[{PEOPLE_DIR}/{HOST_NOTE}]] · [[{DIARY_DIR}/{day}]]"
    return (
        "---\n"
        f"source: {fact.source.value}\n"
        f"importance: {fact.importance}\n"
        f"created: {json.dumps(fact.created_at.isoformat())}\n"
        "tags: [факт]\n"
        "---\n"
        f"{fact.text.strip()}\n\n{_FOOTER_LABEL} {links}\n"
    )


def _properties(text: str) -> tuple[dict[str, str], str]:
    match = _PROPERTIES.match(text)
    if match is None:
        msg = "нет блока свойств в начале заметки"
        raise BadNoteError(msg)
    properties = {}
    for line in match["props"].splitlines():
        key, separator, value = line.partition(":")
        if separator:
            properties[key.strip()] = value.strip().strip("\"'")
    return properties, text[match.end() :]


def parse_fact(text: str, note: str) -> Fact:
    """Факт из заметки; текст — всё до строки со ссылками, её пользователь может и удалить.

    Raises:
        BadNoteError: нет свойств, значение не то или текст пуст.

    """
    properties, body = _properties(text.replace("\r\n", "\n"))
    kept = [line for line in body.splitlines() if not line.startswith(_FOOTER_LABEL)]
    fact_text = "\n".join(kept).strip()
    if not fact_text:
        msg = "в заметке нет текста факта"
        raise BadNoteError(msg)
    try:
        return Fact(
            fact_text,
            FactSource(properties["source"]),
            float(properties["importance"]),
            datetime.fromisoformat(properties["created"]),
            note=note,
        )
    except (KeyError, ValueError) as exc:
        msg = f"неверное свойство заметки: {exc}"
        raise BadNoteError(msg) from exc


def render_turn(turn: Turn, when: datetime) -> str:
    """Ход в заметке чата; строки текста, похожие на разметку, экранируются."""
    flags = [_INTERRUPTED] * turn.is_interrupted + [_EXTERNAL] * turn.is_external
    suffix = f" ({', '.join(flags)})" if flags else ""
    user = _NEEDS_ESCAPE.sub(r"\\", turn.user_text)
    reply = _NEEDS_ESCAPE.sub(r"\\", turn.reply_text)
    return f"## {when:%H:%M:%S}{suffix}\n{_USER_LABEL}{user}\n{_REPLY_LABEL}{reply}\n\n"


@dataclass(frozen=True, slots=True)
class _Block:
    flags: str
    body: str


def _blocks(text: str) -> list[_Block]:
    headings = list(_TURN_HEADING.finditer(text))
    ends = [*(heading.start() for heading in headings[1:]), len(text)]
    return [
        _Block(heading["flags"] or "", text[heading.end() : end])
        for heading, end in zip(headings, ends, strict=True)
    ]


def parse_chat(text: str) -> list[Turn]:
    """Ходы заметки чата по порядку; блок, правленный так, что не разбирается, пропускается."""
    turns = []
    for block in _blocks(text.replace("\r\n", "\n")):
        body = block.body.strip("\n")
        user, separator, reply = body.partition(f"\n{_REPLY_LABEL}")
        if separator and user.startswith(_USER_LABEL):
            turns.append(
                Turn(
                    TurnId(0),
                    _ESCAPED.sub("", user.removeprefix(_USER_LABEL)),
                    _ESCAPED.sub("", reply),
                    is_interrupted=_INTERRUPTED in block.flags,
                    is_external=_EXTERNAL in block.flags,
                )
            )
    return turns


def render_host_note() -> str:
    """Заметка-узел: к ней сходятся факты, поэтому граф Obsidian не рассыпается на точки."""
    return "---\ntags: [человек]\n---\nВедущий: всё, что витюбер запомнил о нём, ссылается сюда.\n"


def render_diary_line(note: str) -> str:
    """Строка дневника о новом факте."""
    return f"- [[{FACTS_DIR}/{note}]]\n"
