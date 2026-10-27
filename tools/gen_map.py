"""Генерирует docs/ai/PROJECT_MAP.md из docstring-ов и публичных символов пакетов.

Запуск: `python tools/gen_map.py`; `--check` — код 1, если карта устарела (для pre-commit и CI).
"""

import ast
import sys
from collections.abc import Iterator
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "vtuber"
OUT = ROOT / "docs" / "ai" / "PROJECT_MAP.md"
HEADER = (
    "# PROJECT MAP",
    "",
    "> Автогенерация: `python tools/gen_map.py`. Не редактировать.",
    "",
)
_SYMBOLS = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
type _Documented = ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef


def _summary(node: _Documented) -> str:
    return (ast.get_docstring(node) or "—").partition("\n")[0]


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _entries(module: Path, root: Path) -> Iterator[str]:
    location = module.relative_to(root).as_posix()
    for node in _parse(module).body:
        if isinstance(node, _SYMBOLS) and not node.name.startswith("_"):
            yield f"- `{node.name}` — `{location}:{node.lineno}` — {_summary(node)}"


def render(src: Path, root: Path) -> str:
    """Строит текст карты: раздел на каждый пакет в src, публичные символы его модулей."""
    lines = list(HEADER)
    for init in sorted(src.rglob("__init__.py")):
        package = init.parent
        lines += [f"## {package.relative_to(root).as_posix()}", _summary(_parse(init))]
        modules = sorted(package.glob("*.py"))
        if entries := [entry for module in modules for entry in _entries(module, root)]:
            lines += ["", *entries]
        lines.append("")
    return "\n".join(lines)


def is_up_to_date(content: str, out: Path) -> bool:
    """Совпадает ли сохранённая карта с только что построенной."""
    return out.is_file() and out.read_text(encoding="utf-8") == content


def main(argv: list[str]) -> int:
    """Пишет карту или, с `--check`, сообщает об устаревшей карте кодом 1."""
    content = render(SRC, ROOT)
    if "--check" not in argv:
        OUT.write_text(content, encoding="utf-8", newline="\n")
        return 0
    if is_up_to_date(content, OUT):
        return 0
    print("docs/ai/PROJECT_MAP.md устарел — запустите: uv run python tools/gen_map.py")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
