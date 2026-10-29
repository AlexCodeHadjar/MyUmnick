"""Долговременные факты (FR-10): извлечь из хода, отсеять повторы, запомнить с вектором.

Повтор определяется по смыслу, а не по строке: факт, чей вектор ближе `dedup_score` к уже
записанному, не добавляется. Задача перезапускаемая (T-13): прерванная и запущенная снова, она
не запишет факт дважды — его найдёт та же проверка.
"""

from collections.abc import Sequence
from datetime import datetime

from pydantic import Field

from vtuber.application.memory.fact_extractor import ExtractedFact, FactExtractor
from vtuber.domain import EmbedKind, Fact, FactSource, Turn, Vector
from vtuber.kernel import ConfigSection, get_logger
from vtuber.ports import EmbedderPort, MemoryStorePort

_log = get_logger(__name__)


class FactMemoryConfig(ConfigSection):
    """`dedup_score` — близость (косинус), от которой новый факт считается уже известным."""

    dedup_score: float = Field(gt=0, le=1)


class FactMemory:
    """Факты о пользователе: извлечение (LLM), векторы (эмбеддер), хранилище."""

    def __init__(
        self,
        extractor: FactExtractor,
        embedder: EmbedderPort,
        store: MemoryStorePort,
        cfg: FactMemoryConfig,
    ) -> None:
        self._extractor = extractor
        self._embedder = embedder
        self._store = store
        self._cfg = cfg

    async def learn(self, turn: Turn, when: datetime) -> int:
        """Запоминает новые факты из хода; возвращает, сколько записано.

        Raises:
            LLMUnavailable, GenerationFailed: извлечение не удалось (кривой JSON — тоже).
            MemoryUnavailable: эмбеддер или хранилище недоступны.

        """
        facts = _unique(await self._extractor.extract(turn))
        if not facts:
            return 0
        vectors = await self._embedder.embed([f.text for f in facts], EmbedKind.PASSAGE)
        stored = 0
        for fact, vector in zip(facts, vectors, strict=True):
            if await self._known(vector):
                _log.debug("memory.fact_known", text=fact.text)
                continue
            await self._store.add(
                Fact(fact.text, FactSource.EXTRACTED, fact.importance, when), vector
            )
            stored += 1
        _log.info("memory.facts_learned", turn=turn.id, extracted=len(facts), stored=stored)
        return stored

    async def _known(self, vector: Vector) -> bool:
        hits = await self._store.search(vector, limit=1)
        return bool(hits) and hits[0].score >= self._cfg.dedup_score


def _unique(facts: Sequence[ExtractedFact]) -> list[ExtractedFact]:
    """Повторы внутри одного ответа модели — по тексту без регистра."""
    seen: set[str] = set()
    unique: list[ExtractedFact] = []
    for fact in facts:
        key = fact.text.casefold()
        if key not in seen:
            seen.add(key)
            unique.append(fact)
    return unique
