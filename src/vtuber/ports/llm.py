"""Порт языковой модели: потоковая генерация ответа и прогрев KV-кэша."""

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Protocol

from vtuber.domain import Message


@dataclass(frozen=True, slots=True)
class GenerationParams:
    """Параметры генерации; значения приходят из конфига (`[llm.generation]`, ADR-0006)."""

    max_tokens: int
    temperature: float
    stop: tuple[str, ...] = ()


class LLMPort(Protocol):
    """Локальная LLM; адаптеры бросают только доменные ошибки (R-43).

    Контракт для каждого адаптера — `tests/contract/test_llm_contract.py` (R-57).
    """

    def stream(self, messages: Sequence[Message], params: GenerationParams) -> AsyncIterator[str]:
        """Отдаёт текстовые дельты ответа по мере генерации (T-01).

        Отмена задачи-потребителя обязана закрыть поток генерации, чтобы бэкенд перестал
        работать впустую (T-14); `CancelledError` не подавляется (R-38).

        Raises:
            LLMUnavailable: бэкенд не отвечает или не загружен.
            GenerationFailed: бэкенд ответил, но генерация сорвалась посреди ответа.

        """

    async def prefill(self, messages: Sequence[Message]) -> None:
        """Прогревает KV-кэш промптом без генерации (T-05, T-06).

        Raises:
            LLMUnavailable: бэкенд не отвечает или не загружен.

        """
