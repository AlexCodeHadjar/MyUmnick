"""Секция `[llm]`: выбор и подключение LLM-сервера, параметры генерации."""

from pydantic import Field

from vtuber.kernel import ConfigSection


class LlamaCppOptions(ConfigSection):
    """Подсекция `[llm.llamacpp]`: особенности llama-server.

    `slot_id` — слот диалога: его KV-кэш переиспользуется между ходами (T-03); фон Этапа 10
    работает в другом слоте. `enable_thinking` — reasoning-режим шаблона чата (T-08: выключен).
    `forbid_foreign_scripts` — запрет алфавитов, которых нет в русской речи (ADR-0004);
    `forbid_cyrillic` — ещё и кириллицы: английское издание (Этап 20) отвечает только по-английски.
    """

    slot_id: int
    enable_thinking: bool
    forbid_foreign_scripts: bool
    forbid_cyrillic: bool


class GenerationConfig(ConfigSection):
    """Подсекция `[llm.generation]`: длина и температура ответа диалога (T-07)."""

    max_tokens: int = Field(gt=0)
    temperature: float = Field(ge=0)


class LLMConfig(ConfigSection):
    """Какой бэкенд, где он, тайм-ауты (R-36) и параметры генерации.

    `backend` — имя адаптера в реестре bootstrap (`llamacpp`, `openai_compat`).
    `read_timeout_s` — максимум ожидания следующей порции, включая prefill длинного промпта.
    """

    backend: str
    base_url: str
    model: str
    connect_timeout_s: float
    read_timeout_s: float
    llamacpp: LlamaCppOptions
    generation: GenerationConfig
