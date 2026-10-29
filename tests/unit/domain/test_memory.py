from datetime import UTC, datetime

import pytest

from vtuber.domain import Fact, FactSource

WHEN = datetime(2026, 10, 29, tzinfo=UTC)


def test_fact_keeps_its_fields() -> None:
    fact = Fact("Любит котов", FactSource.USER, 0.7, WHEN)

    assert (fact.text, fact.source, fact.importance, fact.created_at) == (
        "Любит котов",
        FactSource.USER,
        0.7,
        WHEN,
    )


@pytest.mark.parametrize("importance", [-0.1, 1.1])
def test_importance_outside_unit_range_is_rejected(importance: float) -> None:
    with pytest.raises(ValueError, match="важность"):
        Fact("x", FactSource.USER, importance, WHEN)


def test_naive_datetime_is_rejected() -> None:
    with pytest.raises(ValueError, match="часовым поясом"):
        Fact("x", FactSource.SUMMARY, 0.5, datetime(2026, 10, 29))  # noqa: DTZ001 — проверяем отказ
