"""Профиль содержания (Этап 20, ADR-0033): правила рамки и входной фильтр жёсткого минимума.

Правила профиля дописываются к правилам персоны при сборке: файл персоны их не удалит, а системный
промпт остаётся одинаковым на всех ходах (T-03). Профиль `standard` ничего не добавляет — русское
издание байт в байт прежнее. Входной фильтр — обёртка `LLMPort`: реплика, пересекающая минимум,
до модели не доходит, отказ звучит сразу (ноль задержки для обычных реплик, кроме регулярки).
"""

from collections.abc import AsyncGenerator, Sequence
from contextlib import aclosing
from dataclasses import replace

from vtuber.application.prompting.texts import ProfileTexts
from vtuber.domain import ContentProfile, Message, Persona, Role, crosses_hard_floor
from vtuber.kernel import get_logger
from vtuber.ports import GenerationParams, LLMPort

_log = get_logger(__name__)


def with_profile(
    persona: Persona, texts: ProfileTexts, profile: ContentProfile, *, stream_safe: bool
) -> Persona:
    """Персона с правилами профиля: без цензуры — разрешение и минимум; эфир — правила площадок."""
    if profile is ContentProfile.STANDARD:
        return persona
    extra = (*texts.unfiltered, *texts.floor, *(texts.stream if stream_safe else ()))
    return replace(persona, rules=(*persona.rules, *extra))


class FloorGuard:
    """`LLMPort`: реплика пересекает жёсткий минимум — отказ в образе без вызова модели."""

    def __init__(self, inner: LLMPort, refusal: str) -> None:
        self._inner = inner
        self._refusal = refusal

    async def stream(
        self, messages: Sequence[Message], params: GenerationParams
    ) -> AsyncGenerator[str]:
        """Поток внутренней модели или готовый отказ."""
        last = messages[-1] if messages else None
        if last is not None and last.role is Role.USER and crosses_hard_floor(last.text):
            _log.warning("floor.blocked")
            yield self._refusal
            return
        async with aclosing(self._inner.stream(messages, params)) as deltas:
            async for delta in deltas:
                yield delta

    async def prefill(self, messages: Sequence[Message]) -> None:
        """Прогрев — как у внутренней модели."""
        await self._inner.prefill(messages)
