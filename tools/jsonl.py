"""Чтение JSONL-наборов (бенчмарк, eval) с проверкой pydantic и номером строки в ошибке."""

from pathlib import Path

from pydantic import BaseModel, ValidationError


class JsonlError(ValueError):
    """Строка набора не разбирается или не проходит проверку."""


def read_jsonl[M: BaseModel](path: Path, model: type[M]) -> list[M]:
    """Читает по одной модели `model` из каждой непустой строки файла.

    Raises:
        JsonlError: строка — не JSON или не проходит проверку; в сообщении `файл:строка`.

    """
    rows: list[M] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(model.model_validate_json(line))
        except ValidationError as exc:
            msg = f"{path.as_posix()}:{number}: {exc}"
            raise JsonlError(msg) from exc
    return rows
