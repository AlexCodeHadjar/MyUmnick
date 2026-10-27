"""Раздел карты проекта для UI: модули TypeScript и компоненты Svelte из `ui/src`.

Без разбора TS: экспорт ищется регулярным выражением по началу строки, описание — первая строка
JSDoc/`//`-комментария над ним. Этого хватает: код UI отформатирован prettier, экспорт всегда с
начала строки.
"""

import re
from collections.abc import Iterator
from pathlib import Path

_EXPORT = re.compile(
    r"^export\s+(?:default\s+)?(?:abstract\s+)?(?:async\s+)?"
    r"(?:class|function|const|let|type|interface|enum)\s+([A-Za-z_$][\w$]*)"
)
_SOURCE_SUFFIXES = (".ts", ".svelte")
# Тесты и объявления типов окружения — не часть API.
_SKIPPED_SUFFIXES = (".test.ts", ".d.ts")
_COMMENT_STARTS = ("/**", "*", "//")
_NO_DOC = "—"


def _comment_text(line: str) -> str:
    """Текст строки комментария без `/**`, `*`, `*/` и `//`."""
    text = line.strip().removeprefix("/**").removeprefix("//").removesuffix("*/").strip()
    return text.removeprefix("*").strip()


def first_comment(lines: list[str]) -> str:
    """Первая строка ведущего комментария; открывающий `<script>` компонента пропускается."""
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("<script"):
            continue
        if not stripped.startswith(_COMMENT_STARTS):
            return _NO_DOC
        if text := _comment_text(stripped):
            return text
    return _NO_DOC


def _doc_above(lines: list[str], index: int) -> str:
    start = index
    while start > 0 and lines[start - 1].strip().startswith(_COMMENT_STARTS):
        start -= 1
    return first_comment(lines[start:index])


def _is_source(path: Path) -> bool:
    name = path.name
    return name.endswith(_SOURCE_SUFFIXES) and not name.endswith(_SKIPPED_SUFFIXES)


def _read(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _file_entries(path: Path, root: Path) -> Iterator[str]:
    location = path.relative_to(root).as_posix()
    lines = _read(path)
    # Компонент и сгенерированный файл — одной строкой: их API — сам файл.
    if path.suffix == ".svelte" or path.name.endswith(".gen.ts"):
        yield f"- `{path.name}` — `{location}:1` — {first_comment(lines)}"
        return
    for index, line in enumerate(lines):
        if match := _EXPORT.match(line):
            yield f"- `{match[1]}` — `{location}:{index + 1}` — {_doc_above(lines, index)}"


def render_ui(src: Path, root: Path) -> list[str]:
    """Раздел на каждый каталог `ui/src` с кодом; описание каталога — из его `index.ts`."""
    lines: list[str] = []
    directories = sorted({path.parent for path in src.rglob("*") if _is_source(path)})
    for directory in directories:
        index = directory / "index.ts"
        summary = first_comment(_read(index)) if index.is_file() else _NO_DOC
        lines += [f"## {directory.relative_to(root).as_posix()}", summary]
        files = sorted(path for path in directory.iterdir() if _is_source(path))
        if entries := [entry for path in files for entry in _file_entries(path, root)]:
            lines += ["", *entries]
        lines.append("")
    return lines
