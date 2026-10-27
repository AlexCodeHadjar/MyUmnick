"""Секция `[llm]`: подключение к LLM-серверу, общая для адаптеров llm."""

from vtuber.kernel import ConfigSection


class LLMConfig(ConfigSection):
    """Адрес и тайм-ауты LLM-сервера (R-36).

    `read_timeout_s` — максимум ожидания следующей порции, включая prefill длинного промпта.
    """

    base_url: str
    model: str
    connect_timeout_s: float
    read_timeout_s: float
