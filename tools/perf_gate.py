"""Гейт регрессий (S-9.4): p95 хуже опорного больше чем на 15 % — провал.

Запуск: `uv run python -m tools.perf_gate опорный.json текущий.json [--limit 0.15]`. Файлы пишет
бенчмарк: `{"machine": "...", "metrics": {"имя": {"p50": 1.0, "p95": 2.0}}}`. Цифры с разных машин
не сравниваются: такой прогон ничего не доказывает, и код возврата у него свой.
"""

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TextIO

from pydantic import BaseModel, ConfigDict, ValidationError

DEFAULT_LIMIT: Final = 0.15
MIN_GROWTH_MS: Final = 1.0
"""Меньший рост не считается: на доле миллисекунды проценты — это шум повторных прогонов (±27 %)."""
EXIT_REGRESSION: Final = 1
EXIT_NOT_COMPARABLE: Final = 2
PERCENT: Final = 100


class Stats(BaseModel):
    """Перцентили одной метрики, мс."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    p50: float
    p95: float


class PerfReport(BaseModel):
    """Отчёт бенчмарка."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    machine: str
    metrics: dict[str, Stats]


@dataclass(frozen=True, slots=True)
class Finding:
    """Что не так с метрикой; `base` и `now` — p95 или None, если метрики нет."""

    metric: str
    base: float
    now: float | None


def regressions(base: PerfReport, now: PerfReport, limit: float) -> list[Finding]:
    """Метрика пропала — тоже провал: иначе регрессию можно спрятать, перестав её считать."""
    findings = []
    for name, stats in base.metrics.items():
        current = now.metrics.get(name)
        if current is None:
            findings.append(Finding(name, stats.p95, None))
        elif current.p95 > stats.p95 * (1 + limit) and current.p95 - stats.p95 >= MIN_GROWTH_MS:
            findings.append(Finding(name, stats.p95, current.p95))
    return findings


def _render(finding: Finding) -> str:
    if finding.now is None:
        return f"x {finding.metric}: метрики больше нет (было p95 {finding.base:.2f} мс)"
    growth = PERCENT * (finding.now / finding.base - 1) if finding.base > 0 else float("inf")
    return f"x {finding.metric}: p95 {finding.base:.2f} → {finding.now:.2f} мс (+{growth:.0f} %)"


def main(argv: Sequence[str], out: TextIO) -> int:
    """Код возврата: 0 — в норме, 1 — регрессия, 2 — сравнивать нельзя."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument("--limit", type=float, default=DEFAULT_LIMIT)
    args = parser.parse_args(argv)
    try:
        base = PerfReport.model_validate_json(args.baseline.read_text(encoding="utf-8"))
        now = PerfReport.model_validate_json(args.current.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        print(f"Не прочитать отчёт: {exc}", file=out)
        return EXIT_NOT_COMPARABLE
    if base.machine != now.machine:
        print(f"Разные машины: {base.machine} и {now.machine}; сравнивать нельзя", file=out)
        return EXIT_NOT_COMPARABLE
    findings = regressions(base, now, args.limit)
    for finding in findings:
        print(_render(finding), file=out)
    print(f"Метрик: {len(base.metrics)}, регрессий: {len(findings)}", file=out)
    return EXIT_REGRESSION if findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:], sys.stdout))
