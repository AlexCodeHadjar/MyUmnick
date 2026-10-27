from pathlib import Path

import pytest
from pydantic import BaseModel

from tools.jsonl import JsonlError, read_jsonl


class _Row(BaseModel):
    id: str
    value: int


def test_reads_one_model_per_non_empty_line(tmp_path: Path) -> None:
    path = tmp_path / "rows.jsonl"
    path.write_text('{"id": "a", "value": 1}\n\n{"id": "б", "value": 2}\n', encoding="utf-8")

    assert read_jsonl(path, _Row) == [_Row(id="a", value=1), _Row(id="б", value=2)]


@pytest.mark.parametrize("line", ["{не json", '{"id": "a"}', '{"id": "a", "value": "x"}'])
def test_bad_line_is_reported_with_file_and_line_number(tmp_path: Path, line: str) -> None:
    path = tmp_path / "rows.jsonl"
    path.write_text(f'{{"id": "ok", "value": 1}}\n{line}\n', encoding="utf-8")

    with pytest.raises(JsonlError, match=r"rows\.jsonl:2"):
        read_jsonl(path, _Row)
