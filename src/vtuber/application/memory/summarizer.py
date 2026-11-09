"""Резюме отрезанной части истории (T-04): старший блок ходов заменяется кратким пересказом.

Работает в простое (T-13) через слот 1 LLM. Новое резюме вбирает прежнее: история сколько угодно
длинная, а резюме — одно и ограничено `MAX_SUMMARY_CHARS`, чтобы не съесть бюджет контекста.
"""

from collections.abc import Sequence
from typing import Final

from vtuber.application.memory.llm_text import collect, strip_tags
from vtuber.application.memory.texts import RU_MEMORY, MemoryTexts
from vtuber.domain import GenerationFailed, Message, Role
from vtuber.ports import GenerationParams, LLMPort

MAX_SUMMARY_CHARS: Final = 1200
SUMMARY_PROMPT: Final = RU_MEMORY.summary_prompt  # прежнее имя: русское издание


class Summarizer:
    """Прежнее резюме + отрезанные сообщения → новое резюме одним запросом к LLM."""

    def __init__(
        self, llm: LLMPort, params: GenerationParams, texts: MemoryTexts = RU_MEMORY
    ) -> None:
        self._llm = llm
        self._params = params
        self._texts = texts

    async def summarize(self, previous: str | None, dropped: Sequence[Message]) -> str:
        """Новое резюме, не длиннее `MAX_SUMMARY_CHARS` (обрезается по предложению).

        Raises:
            LLMUnavailable: LLM-сервер недоступен.
            GenerationFailed: генерация сорвалась или ответ пуст.

        """
        texts = self._texts
        speakers = {Role.USER: texts.user_label, Role.ASSISTANT: texts.assistant_label}
        lines = [f"{speakers.get(m.role, m.role)}: {strip_tags(m.text)}" for m in dropped]
        intro = texts.previous_summary.format(summary=previous) if previous else ""
        request = "\n".join(part for part in (intro, texts.fragment, *lines) if part)
        messages = (Message(Role.SYSTEM, texts.summary_prompt), Message(Role.USER, request))
        summary = " ".join((await collect(self._llm, messages, self._params)).split())
        if not summary:
            msg = "LLM вернула пустое резюме истории"
            raise GenerationFailed(msg)
        return _clip(summary)


def _clip(text: str) -> str:
    if len(text) <= MAX_SUMMARY_CHARS:
        return text
    cut = text[:MAX_SUMMARY_CHARS]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return cut[: end + 1] if end > 0 else cut
