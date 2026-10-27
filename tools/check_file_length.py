"""Проверяет лимит длины Python-файлов (R-10): не больше 250 строк кода на файл.

Строка кода — строка, где есть хотя бы один токен, кроме комментария. Пустые строки,
комментарии и docstring-и не считаются.
Запуск: `python tools/check_file_length.py [файлы...]` (без аргументов — src, tests, tools).
"""

import ast
import io
import sys
import tokenize
from pathlib import Path

MAX_CODE_LINES = 250
DEFAULT_ROOTS = ("src", "tests", "tools")
_NON_CODE_TOKENS = frozenset(
    {
        tokenize.COMMENT,
        tokenize.NL,
        tokenize.NEWLINE,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.ENCODING,
        tokenize.ENDMARKER,
    }
)
_DOCUMENTED = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def _docstring_lines(tree: ast.Module) -> set[int]:
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, _DOCUMENTED) and ast.get_docstring(node, clean=False) is not None:
            docstring = node.body[0]
            lines.update(range(docstring.lineno, (docstring.end_lineno or docstring.lineno) + 1))
    return lines


def count_code_lines(source: str) -> int:
    """Считает строки кода в исходнике без пустых строк, комментариев и docstring-ов."""
    code_lines: set[int] = set()
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type not in _NON_CODE_TOKENS:
            code_lines.update(range(token.start[0], token.end[0] + 1))
    return len(code_lines - _docstring_lines(ast.parse(source)))


def find_violations(paths: list[Path]) -> list[str]:
    """Возвращает сообщения о файлах, превысивших лимит R-10."""
    counted = ((path, count_code_lines(path.read_text(encoding="utf-8"))) for path in paths)
    return [
        f"{path.as_posix()}: {lines} строк кода > {MAX_CODE_LINES} (R-10) — разделите модуль"
        for path, lines in counted
        if lines > MAX_CODE_LINES
    ]


def main(argv: list[str]) -> int:
    """Проверяет файлы из argv или все .py в DEFAULT_ROOTS; код 1 — есть нарушения."""
    paths = [Path(arg) for arg in argv] or [
        path for root in DEFAULT_ROOTS for path in sorted(Path(root).rglob("*.py"))
    ]
    violations = find_violations(paths)
    for message in violations:
        print(message)
    return int(bool(violations))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
