import pytest

from tools.bench_memory import Timing, memory_cost_ms


def test_cost_ignores_the_order_of_the_pair() -> None:
    # Второй в паре всегда быстрее на 100 мс, память стоит 10 мс.
    timings = [Timing("a", 360, 270), Timing("b", 260, 370)] * 4
    assert memory_cost_ms(timings) == pytest.approx(10)


def test_no_pairs_no_cost() -> None:
    assert memory_cost_ms([]) == 0.0
