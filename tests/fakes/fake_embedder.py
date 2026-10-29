"""FakeEmbedder: детерминированные векторы без модели (R-56) — хэш символьных триграмм.

Тексты с общими словами получают близкие векторы, без общих — далёкие: этого хватает, чтобы
проверять поиск по смыслу в тестах сервиса памяти, не загружая e5.
"""

import hashlib
import math
from collections.abc import Sequence
from dataclasses import dataclass, field

from vtuber.domain import EmbedKind, MemoryUnavailable, Vector

NGRAM = 3


@dataclass(slots=True)
class FakeEmbedder:
    """Реализует EmbedderPort. `available=False` — модель «не загружена». Запросы — в `calls`."""

    dimensions: int = 64
    available: bool = True
    calls: list[tuple[tuple[str, ...], EmbedKind]] = field(default_factory=list)

    async def embed(self, texts: Sequence[str], kind: EmbedKind) -> list[Vector]:
        if not self.available:
            msg = "FakeEmbedder: модель не загружена (сценарий теста)"
            raise MemoryUnavailable(msg)
        self.calls.append((tuple(texts), kind))
        return [self._vector(text) for text in texts]

    def _vector(self, text: str) -> Vector:
        counts = [0.0] * self.dimensions
        for gram in _trigrams(text):
            digest = hashlib.blake2b(gram.encode(), digest_size=4).digest()
            counts[int.from_bytes(digest) % self.dimensions] += 1
        norm = math.sqrt(sum(value * value for value in counts))
        if norm == 0:
            # Пустой текст — тоже единичный вектор: контракт не делает для него исключения.
            return (1.0, *([0.0] * (self.dimensions - 1)))
        return tuple(value / norm for value in counts)


def _trigrams(text: str) -> list[str]:
    words = "".join(ch if ch.isalnum() else " " for ch in text.lower()).split()
    return [
        padded[i : i + NGRAM]
        for padded in (f" {word} " for word in words)
        for i in range(len(padded) - NGRAM + 1)
    ]
