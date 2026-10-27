"""Секция `[llm]`: подключение к LLM-серверу, общая для адаптеров llm."""

from vtuber.kernel import ConfigSection


class LlamaCppOptions(ConfigSection):
    """Подсекция `[llm.llamacpp]`: особенности llama-server.

    `slot_id` — слот диалога: его KV-кэш переиспользуется между ходами (T-03); фон Этапа 10
    работает в другом слоте. `enable_thinking` — reasoning-режим шаблона чата (T-08: выключен).
    """

    slot_id: int
    enable_thinking: bool


class LLMConfig(ConfigSection):
    """Адрес и тайм-ауты LLM-сервера (R-36).

    `read_timeout_s` — максимум ожидания следующей порции, включая prefill длинного промпта.
    """

    base_url: str
    model: str
    connect_timeout_s: float
    read_timeout_s: float
    llamacpp: LlamaCppOptions
