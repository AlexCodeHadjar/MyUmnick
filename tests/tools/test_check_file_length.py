from pathlib import Path

from tools.check_file_length import MAX_CODE_LINES, count_code_lines, find_violations, main


def test_blank_lines_and_comments_are_not_code() -> None:
    source = "# комментарий\n\nx = 1  # хвостовой комментарий\n\n# ещё\ny = 2\n"
    assert count_code_lines(source) == 2


def test_docstrings_are_not_code() -> None:
    source = '"""Модуль.\n\nПодробно.\n"""\n\n\ndef f() -> None:\n    """Функция."""\n    pass\n'
    assert count_code_lines(source) == 2


def test_multiline_statement_counts_every_line() -> None:
    source = 'value = (\n    1,\n    2,\n)\ntext = """a\nb"""\n'
    assert count_code_lines(source) == 6


def test_file_over_limit_is_reported(tmp_path: Path) -> None:
    long_file = tmp_path / "long.py"
    long_file.write_text("x = 1\n" * (MAX_CODE_LINES + 1), encoding="utf-8")
    short_file = tmp_path / "short.py"
    short_file.write_text("x = 1\n" * MAX_CODE_LINES, encoding="utf-8")

    violations = find_violations([long_file, short_file])

    assert len(violations) == 1
    assert "long.py" in violations[0]
    assert "R-10" in violations[0]


def test_main_returns_nonzero_on_violation(tmp_path: Path) -> None:
    long_file = tmp_path / "long.py"
    long_file.write_text("x = 1\n" * (MAX_CODE_LINES + 1), encoding="utf-8")

    assert main([str(long_file)]) == 1
    assert main([]) == 0
