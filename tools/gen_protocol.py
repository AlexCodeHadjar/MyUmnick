"""Генерирует TS-типы протокола и docs/protocol.md из моделей `vtuber.gateway.protocol`.

Запуск: `uv run python tools/gen_protocol.py`; `--check` — код 1, если файлы устарели.
Модели — единственный источник схемы (R-64): руками сгенерированное не правится.
"""

import json
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Final

from pydantic import TypeAdapter

from vtuber.gateway import (
    AUDIO_FRAME_HEADER_SIZE,
    AUDIO_FRAME_TYPE,
    PROTOCOL_VERSION,
    InboundMessage,
    OutboundMessage,
)

ROOT: Final = Path(__file__).resolve().parent.parent
TS_OUT: Final = ROOT / "ui" / "src" / "core" / "protocol.gen.ts"
DOC_OUT: Final = ROOT / "docs" / "protocol.md"
REF_PREFIX: Final = "#/$defs/"
KIND_TS: Final = MappingProxyType(
    {
        "string": "string",
        "integer": "number",
        "number": "number",
        "boolean": "boolean",
        "null": "null",
        "object": "Record<string, never>",  # объект без полей (EmptyData)
    }
)
NOTICE: Final = "Автогенерация: `uv run python tools/gen_protocol.py`. Не редактировать."

type Schema = Mapping[str, object]


def _schemas() -> tuple[Schema, Schema]:
    inbound = TypeAdapter[InboundMessage](InboundMessage).json_schema(mode="validation")
    outbound = TypeAdapter[OutboundMessage](OutboundMessage).json_schema(mode="serialization")
    return inbound, outbound


def _defs(*schemas: Schema) -> dict[str, Schema]:
    merged: dict[str, Schema] = {}
    for schema in schemas:
        defs = schema.get("$defs", {})
        if isinstance(defs, dict):
            merged.update(defs)
    return dict(sorted(merged.items()))


def _union_names(schema: Schema) -> list[str]:
    variants = schema.get("oneOf", [])
    return [_ref_name(variant) for variant in variants] if isinstance(variants, list) else []


def _ref_name(schema: object) -> str:
    ref = schema.get("$ref", "") if isinstance(schema, dict) else ""
    return str(ref).removeprefix(REF_PREFIX)


def ts_type(schema: Schema) -> str:
    """TS-тип для узла JSON Schema (поднабор, который порождают модели протокола)."""
    if "$ref" in schema:
        return _ref_name(schema)
    if "const" in schema:
        return json.dumps(schema["const"], ensure_ascii=False)
    variants = schema.get("enum") or schema.get("anyOf") or schema.get("oneOf")
    if isinstance(variants, list):
        return " | ".join(_variant(variant) for variant in variants)
    return KIND_TS.get(str(schema.get("type", "")), "unknown")


def _variant(variant: object) -> str:
    if isinstance(variant, dict):
        return ts_type(variant)
    return json.dumps(variant, ensure_ascii=False)


def _properties(schema: Schema) -> dict[str, Schema]:
    properties = schema.get("properties", {})
    return dict(properties) if isinstance(properties, dict) else {}


def _ts_definition(name: str, schema: Schema) -> Iterator[str]:
    description = schema.get("description")
    if description:
        yield f"/** {str(description).splitlines()[0]} */"
    properties = _properties(schema)
    if schema.get("type") != "object" or not properties:
        yield f"export type {name} = {ts_type(schema)};"
        return
    yield f"export interface {name} {{"
    yield from (f"  {field}: {ts_type(prop)};" for field, prop in properties.items())
    yield "}"


def render_ts() -> str:
    """Текст `protocol.gen.ts`: все определения и объединения входящих и исходящих."""
    inbound, outbound = _schemas()
    lines = [f"// {NOTICE}", "", f"export const PROTOCOL_VERSION = {PROTOCOL_VERSION} as const;"]
    for name, schema in _defs(inbound, outbound).items():
        lines += ["", *_ts_definition(name, schema)]
    for alias, schema in (("InboundMessage", inbound), ("OutboundMessage", outbound)):
        lines += ["", f"export type {alias} = {' | '.join(_union_names(schema))};"]
    return "\n".join(lines) + "\n"


def _doc_messages(title: str, schema: Schema, defs: Mapping[str, Schema]) -> Iterator[str]:
    yield f"## {title}"
    for name in _union_names(schema):
        message = defs[name]
        kind = _properties(message)["type"].get("const")
        yield ""
        yield f"### `{kind}` — `{name}`"
        yield ""
        yield str(message.get("description", "")).splitlines()[0]
        data = defs.get(_ref_name(_properties(message)["data"]), {})
        rows = [f"| `{f}` | `{ts_type(p)}` |" for f, p in _properties(data).items()]
        yield from (
            ["", "| Поле `data` | Тип |", "|---|---|", *rows] if rows else ["", "`data`: `{}`"]
        )
    yield ""


def render_doc() -> str:
    """Текст `docs/protocol.md`."""
    inbound, outbound = _schemas()
    defs = _defs(inbound, outbound)
    head = [
        "# Протокол UI ↔ Ядро",
        "",
        f"> {NOTICE}",
        "> Источник — `src/vtuber/gateway/protocol.py`; TS-типы — `ui/src/core/protocol.gen.ts`.",
        "",
        f"Версия протокола: **{PROTOCOL_VERSION}**. Текстовый кадр WebSocket — JSON-конверт",
        '`{"v": 1, "type": "…", "turn": "t-000042", "data": {…}}`; `turn` есть у сообщений хода.',
        "Все поля обязательны; отсутствие значения — явный `null`.",
        "",
    ]
    tail = [
        "## Бинарный аудиокадр (Ядро → UI)",
        "",
        "| Смещение | Размер | Поле |",
        "|---|---|---|",
        f"| 0 | 1 | тип кадра (`{AUDIO_FRAME_TYPE:#04x}` = audio) |",
        "| 1 | 1 | версия протокола |",
        "| 2 | 2 | `seq` (uint16, LE, по модулю 2^16) |",
        "| 4 | 4 | `sample_rate` (uint32, LE) |",
        "| 8 | 8 | `turn_id` (uint64, LE) |",
        f"| {AUDIO_FRAME_HEADER_SIZE} | … | PCM s16le, моно |",
    ]
    body = [*_doc_messages("UI → Ядро", inbound, defs), *_doc_messages("Ядро → UI", outbound, defs)]
    return "\n".join([*head, *body, *tail]) + "\n"


def stale_files() -> list[Path]:
    """Сгенерированные файлы, которые не совпадают с текущими моделями."""
    expected = {TS_OUT: render_ts(), DOC_OUT: render_doc()}
    return [
        path
        for path, text in expected.items()
        if not path.is_file() or path.read_text(encoding="utf-8") != text
    ]


def main(argv: list[str]) -> int:
    """Пишет файлы или, с `--check`, сообщает об устаревших кодом 1."""
    if "--check" in argv:
        stale = stale_files()
        for path in stale:
            print(
                f"{path.relative_to(ROOT).as_posix()} устарел — запустите: {NOTICE.split('`')[1]}"
            )
        return int(bool(stale))
    for path, text in ((TS_OUT, render_ts()), (DOC_OUT, render_doc())):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
