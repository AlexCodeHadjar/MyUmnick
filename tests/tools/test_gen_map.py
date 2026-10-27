from pathlib import Path

from tools.gen_map import is_up_to_date, render


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_package(root: Path) -> Path:
    src = root / "src" / "pkg"
    _write(src / "__init__.py", '"""Корневой пакет."""\n')
    _write(
        src / "chunker.py",
        '"""Модуль."""\n\n\nclass Chunker:\n    """Режет текст.\n\n    Подробности.\n    """\n'
        "\n\ndef _private() -> None:\n    pass\n\n\nasync def run() -> None:\n    pass\n",
    )
    _write(src / "sub" / "__init__.py", "")
    return src


def test_map_lists_packages_with_their_docstring(tmp_path: Path) -> None:
    text = render(_make_package(tmp_path), tmp_path)

    assert "## src/pkg\nКорневой пакет.\n" in text
    assert "## src/pkg/sub\n—\n" in text


def test_map_lists_public_symbols_with_location_and_first_docstring_line(tmp_path: Path) -> None:
    text = render(_make_package(tmp_path), tmp_path)

    assert "- `Chunker` — `src/pkg/chunker.py:4` — Режет текст." in text
    assert "- `run` — `src/pkg/chunker.py:15` — —" in text
    assert "_private" not in text


def test_map_ends_with_single_newline(tmp_path: Path) -> None:
    text = render(_make_package(tmp_path), tmp_path)

    assert text.endswith("\n")
    assert not text.endswith("\n\n")


def test_missing_or_stale_map_is_not_up_to_date(tmp_path: Path) -> None:
    out = tmp_path / "PROJECT_MAP.md"
    assert not is_up_to_date("карта", out)

    out.write_text("старая карта", encoding="utf-8")
    assert not is_up_to_date("карта", out)

    out.write_text("карта", encoding="utf-8")
    assert is_up_to_date("карта", out)
