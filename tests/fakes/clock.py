"""Управляемые часы для тестов замеров, затухания, планировщика и дебаунса."""

from dataclasses import dataclass

NS_PER_MS = 1_000_000


@dataclass(slots=True)
class FakeClock:
    """Время в наносекундах, идёт только по `advance_ms`; заменяет `time.perf_counter_ns`."""

    now_ns: int = 0

    def __call__(self) -> int:
        return self.now_ns

    def advance_ms(self, ms: float) -> None:
        self.now_ns += round(ms * NS_PER_MS)
