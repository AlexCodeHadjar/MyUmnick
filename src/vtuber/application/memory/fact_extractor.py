"""Извлечение фактов о пользователе из хода (S-10.4): LLM отвечает строгим JSON, мусор — ошибка.

Работает в простое (T-13) через отдельный слот LLM (слот 1): кэш диалога в слоте 0 не трогается.
Модели оборачивают JSON в ```json, дописывают пояснения, путают кавычки — разбор берёт первый
объект `{…}` в ответе и проверяет схему; не вышло — `GenerationFailed`, а не падение: фоновая
задача пишет сбой в лог, ход и очередь живут.
"""

from typing import Final

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from vtuber.application.memory.llm_text import collect, strip_tags
from vtuber.application.memory.texts import RU_MEMORY, MemoryTexts
from vtuber.domain import GenerationFailed, Message, Role, Turn
from vtuber.ports import GenerationParams, LLMPort

MAX_FACT_CHARS: Final = 200
EXTRACT_PROMPT: Final = RU_MEMORY.extract_prompt  # прежнее имя: русское издание


class ExtractedFact(BaseModel):
    """Факт из ответа LLM; важность — как её оценила модель."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    text: str = Field(min_length=3, max_length=MAX_FACT_CHARS)
    importance: float = Field(ge=0, le=1)


class _Answer(BaseModel):
    model_config = ConfigDict(extra="ignore")

    facts: list[ExtractedFact]


def parse_facts(raw: str) -> list[ExtractedFact]:
    """Факты из ответа модели; пробелы по краям текста срезаются.

    Raises:
        GenerationFailed: в ответе нет объекта JSON или он не по схеме.

    """
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end < start:
        msg = f"в ответе извлечения фактов нет JSON: {raw[:120]!r}"
        raise GenerationFailed(msg)
    try:
        answer = _Answer.model_validate_json(raw[start : end + 1])
    except ValidationError as exc:
        msg = f"ответ извлечения фактов не по схеме: {exc.errors()[0]['msg']}; {raw[:120]!r}"
        raise GenerationFailed(msg) from exc
    return [fact.model_copy(update={"text": fact.text.strip()}) for fact in answer.facts]


class FactExtractor:
    """Ход → факты о пользователе одним запросом к LLM (низкая temperature — в `params`)."""

    def __init__(
        self, llm: LLMPort, params: GenerationParams, texts: MemoryTexts = RU_MEMORY
    ) -> None:
        self._llm = llm
        self._params = params
        self._texts = texts

    async def extract(self, turn: Turn) -> list[ExtractedFact]:
        """Факты из реплики пользователя (и ответа — как контекста).

        Raises:
            LLMUnavailable: LLM-сервер недоступен.
            GenerationFailed: генерация сорвалась или ответ — не JSON по схеме.

        """
        texts = self._texts
        reply = strip_tags(turn.reply_text)
        dialogue = f"{texts.user_label}: {turn.user_text}\n{texts.assistant_label}: {reply}"
        messages = (
            Message(Role.SYSTEM, texts.extract_prompt),
            Message(Role.USER, dialogue),
        )
        return parse_facts(await collect(self._llm, messages, self._params))
