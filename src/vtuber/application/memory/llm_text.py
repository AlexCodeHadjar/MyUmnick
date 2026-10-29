"""Общее для фоновых запросов памяти к LLM: ответ целиком и текст без тегов эмоций."""

import re
from collections.abc import Sequence
from contextlib import aclosing
from typing import Final

from vtuber.domain import Message
from vtuber.ports import GenerationParams, LLMPort

# Теги эмоций ответа (`<happy>`) в истории есть, а модели памяти они только мешают.
_TAG: Final = re.compile(r"<[a-z]+>")


async def collect(llm: LLMPort, messages: Sequence[Message], params: GenerationParams) -> str:
    """Ответ LLM целиком (фоновым задачам стрим не нужен); поток закрывается при отмене."""
    async with aclosing(llm.stream(messages, params)) as stream:
        return "".join([delta async for delta in stream])


def strip_tags(text: str) -> str:
    """Текст ответа без тегов эмоций."""
    return _TAG.sub("", text).strip()
