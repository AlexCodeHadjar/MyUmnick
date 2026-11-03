"""Гейт поиска по памяти (T-12): искать только там, где память нужна, — иначе 0 мс на ход.

Решение принимается эвристиками без модели (микросекунды): вопрос о прошлом разговоре или о самом
пользователе. Ошибка в сторону «не искать» стоит честного «не помню», ошибка в сторону «искать» —
около 20 мс и справки в промпте: поэтому правила широкие, а лишнее отсекает порог близости.
"""

import asyncio
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from pydantic import Field

from vtuber.domain import EmbedKind, MemoryUnavailable
from vtuber.kernel import ConfigSection, Telemetry, get_logger
from vtuber.ports import EmbedderPort, MemoryStorePort

MS_PER_S: Final = 1000
FACTS_PREFIX: Final = "Ты помнишь о пользователе:"

_RECALL: Final = re.compile(
    r"\b(помни\w*|вспомни\w*|забыл\w*|напомни\w*|говорил\w*|рассказывал\w*|упоминал\w*"
    r"|обсуждали|в прошлый раз|в прошлом разговоре|раньше)\b",
    re.IGNORECASE,
)
_ABOUT_USER: Final = re.compile(
    r"\b(я|мне|меня|мной|мой|моя|моё|мое|мою|мои|моего|моей|моих|моему|моим|моими|моём|моем"
    r"|у меня|обо мне)\b",
    re.IGNORECASE,
)
_QUESTION: Final = re.compile(
    r"\?|\b(кто|что|чем|чего|где|куда|откуда|когда|как|какой|какая|какое|какие|сколько|почему"
    r"|зачем|знаешь|угадай|скажи|расскажи)\b",
    re.IGNORECASE,
)
_FACTUAL: Final = re.compile(
    r"^\s*(кто|что такое|что значит|где|когда|сколько|какой|какая|какое|какие|почему|зачем"
    r"|в каком|в какой|на каком|на какой|чем отличается|как называется)\b",
    re.IGNORECASE,
)
_ME_AS_SUBJECT: Final = re.compile(
    r"\b(как|что|кто|где|когда|сколько|куда)\b.*\b(я|меня|мне|мой|моя|моё|мою|мои|моего|моей)\b",
    re.IGNORECASE,
)

_log = get_logger(__name__)


def needs_memory(text: str) -> bool:
    """Реплика о прошлом разговоре или вопрос о самом пользователе."""
    if _RECALL.search(text):
        return True
    return bool(_ABOUT_USER.search(text) and _QUESTION.search(text))


def is_factual_question(text: str) -> bool:
    """Вопрос о мире, а не о пользователе: на нём цена выдумки выше, температура ниже."""
    return bool(_FACTUAL.search(text)) and not _ME_AS_SUBJECT.search(text)


class RetrievalConfig(ConfigSection):
    """Секция `[memory.retrieval]`.

    `limit` — фактов в справке; `min_score` — порог близости (e5 сжимает шкалу: несвязанное ≈
    0.75); `timeout_ms` — дольше ход не ждёт, идёт без памяти; `factual_temperature` — для вопросов
    о мире.
    """

    limit: int = Field(gt=0)
    min_score: float = Field(gt=0, le=1)
    timeout_ms: int = Field(gt=0)
    factual_temperature: float = Field(ge=0)


@dataclass(frozen=True, slots=True)
class TurnHints:
    """Что память добавляет ходу: справка в реплику и температура (None — обычная)."""

    context: tuple[str, ...] = ()
    temperature: float | None = None


class MemoryRecall:
    """Подсказки хода: факты из памяти, если гейт открыт; сбой памяти ход не задерживает."""

    def __init__(
        self,
        embedder: EmbedderPort,
        store: MemoryStorePort,
        cfg: RetrievalConfig,
        telemetry: Telemetry,
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._cfg = cfg
        self._telemetry = telemetry

    async def hints(self, text: str) -> TurnHints:
        """Подсказки для реплики `text`; гейт закрыт — без единого await дольше шага цикла."""
        factual = is_factual_question(text)
        facts = await self._search(text) if needs_memory(text) else ()
        return TurnHints(
            context=(f"{FACTS_PREFIX} {' '.join(facts)}",) if facts else (),
            temperature=self._cfg.factual_temperature if factual and not facts else None,
        )

    async def _search(self, text: str) -> Sequence[str]:
        try:
            with self._telemetry.span("memory.recall"):
                async with asyncio.timeout(self._cfg.timeout_ms / MS_PER_S):
                    (query,) = await self._embedder.embed([text], EmbedKind.QUERY)
                    hits = await self._store.search(query, self._cfg.limit)
        except MemoryUnavailable as exc:
            _log.info("memory.recall_unavailable", problem=str(exc))
            return ()
        except TimeoutError:
            _log.warning("memory.recall_timeout", timeout_ms=self._cfg.timeout_ms)
            return ()
        return [hit.fact.text for hit in hits if hit.score >= self._cfg.min_score]
