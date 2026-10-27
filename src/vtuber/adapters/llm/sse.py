"""Разбор потока SSE чат-ответа OpenAI-совместимого сервера: строка → текст дельты."""

import json
from typing import Final

from vtuber.domain import GenerationFailed

SSE_DONE: Final = "[DONE]"
_DATA_PREFIX: Final = "data:"


def data_of(line: str) -> str | None:
    """Полезная нагрузка строки `data: …` или None для пустых строк, комментариев и прочих полей."""
    if not line.startswith(_DATA_PREFIX):
        return None
    return line.removeprefix(_DATA_PREFIX).strip()


def delta_text(payload: str) -> str:
    """Текст дельты первого варианта ответа; пустая строка, если в порции текста нет.

    Raises:
        GenerationFailed: порция — не JSON или не похожа на чанк chat.completion.

    """
    try:
        chunk = json.loads(payload)  # boundary: нетипизированный JSON сервера (R-18)
        choices = chunk["choices"]
        if not choices:
            return ""
        content = choices[0]["delta"].get("content")
    except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        msg = f"LLM-сервер прислал неожиданную порцию ответа: {payload[:200]!r}"
        raise GenerationFailed(msg) from exc
    return content if isinstance(content, str) else ""
