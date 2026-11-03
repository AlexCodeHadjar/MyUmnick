"""FakeMemoryStore: факты в списке, поиск полным перебором (R-56)."""

from dataclasses import dataclass, field

from vtuber.domain import Fact, FactHit, FactId, MemoryUnavailable, Vector


@dataclass(slots=True)
class FakeMemoryStore:
    """Реализует MemoryStorePort для векторов размерности `dimensions`.

    `available=False` — хранилище «не открыто». Записи — в `facts` (id = индекс + 1).
    """

    dimensions: int = 64
    available: bool = True
    facts: list[tuple[Fact, Vector]] = field(default_factory=list)

    async def add(self, fact: Fact, vector: Vector) -> FactId:
        self._check(vector)
        self.facts.append((fact, vector))
        return FactId(len(self.facts))

    async def all_facts(self) -> list[Fact]:
        self._check_open()
        return [fact for fact, _ in self.facts]

    async def clear(self) -> None:
        self._check_open()
        self.facts.clear()

    def _check_open(self) -> None:
        if not self.available:
            msg = "FakeMemoryStore: хранилище не открыто (сценарий теста)"
            raise MemoryUnavailable(msg)

    async def search(self, query: Vector, limit: int) -> list[FactHit]:
        self._check(query)
        if limit < 1:
            msg = f"limit поиска — не меньше 1, получено {limit}"
            raise ValueError(msg)
        hits = [
            FactHit(FactId(index + 1), fact, sum(a * b for a, b in zip(query, vector, strict=True)))
            for index, (fact, vector) in enumerate(self.facts)
        ]
        hits.sort(key=lambda hit: hit.score, reverse=True)
        return hits[:limit]

    def _check(self, vector: Vector) -> None:
        if not self.available:
            msg = "FakeMemoryStore: хранилище не открыто (сценарий теста)"
            raise MemoryUnavailable(msg)
        if len(vector) != self.dimensions:
            msg = f"вектор размерности {len(vector)}, хранилище — {self.dimensions}"
            raise ValueError(msg)
