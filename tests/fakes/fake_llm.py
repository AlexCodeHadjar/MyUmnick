"""FakeLLM: детерминированный стрим ответа без сервера и GPU (R-56)."""

import asyncio
from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass, field

from vtuber.domain import LLMUnavailable, Message, VtuberError
from vtuber.ports import GenerationParams

MS_PER_S = 1000


@dataclass(slots=True)
class FakeLLM:
    """Реализует LLMPort: отдаёт `text` порциями по `chunk_size` символов с паузой `delay_ms`.

    `fail_after=N` — бросить `error_type` после N порций (0 — бэкенд недоступен сразу, и в
    `prefill` тоже). Запоминает запросы в `calls` и `prefills` для проверок в тестах.
    """

    text: str
    chunk_size: int = 4
    delay_ms: float = 0
    fail_after: int | None = None
    error_type: type[VtuberError] = LLMUnavailable
    calls: list[tuple[Sequence[Message], GenerationParams]] = field(default_factory=list)
    prefills: list[Sequence[Message]] = field(default_factory=list)

    async def stream(
        self, messages: Sequence[Message], params: GenerationParams
    ) -> AsyncGenerator[str]:
        self.calls.append((messages, params))
        chunks = [
            self.text[i : i + self.chunk_size] for i in range(0, len(self.text), self.chunk_size)
        ]
        for index, chunk in enumerate(chunks):
            if index == self.fail_after:
                raise self._error()
            # sleep(0) тоже уступает цикл: отмена срабатывает между порциями, как у сервера.
            await asyncio.sleep(self.delay_ms / MS_PER_S)
            yield chunk

    async def prefill(self, messages: Sequence[Message]) -> None:
        if self.fail_after == 0:
            raise self._error()
        self.prefills.append(messages)
        await asyncio.sleep(0)

    def _error(self) -> VtuberError:
        return self.error_type(f"FakeLLM: отказ по сценарию теста (fail_after={self.fail_after})")
