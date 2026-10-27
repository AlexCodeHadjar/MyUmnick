"""Оценка качества ответов LLM на эталонных вопросах: правила-проверки, таблица по категориям.

Запуск: `uv run python tools/eval_quality.py [--cases eval/qa_ru.jsonl] [--out отчёт.json]`.
Формат кейса и категории — docs/testing.md («Оценка качества»).
"""

import argparse
import asyncio
import json
import os
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Literal, TextIO

from pydantic import BaseModel, ConfigDict, Field

from tools.eval_checks import Expect, evaluate
from tools.jsonl import read_jsonl
from tools.llm_client import ROOT, SYSTEM_PROMPT, collect, open_llm
from vtuber.domain import LLMUnavailable, Message, Role, VtuberError
from vtuber.ports import GenerationParams, LLMPort

__all__ = [
    "CaseResult",
    "EvalCase",
    "Expect",
    "evaluate",
    "load_cases",
    "main",
    "render",
    "run_case",
]

DEFAULT_CASES: Final = ROOT / "eval" / "qa_ru.jsonl"
REPLY_PREVIEW: Final = 160
PERCENT: Final = 100
EXIT_FAILED: Final = 1
EXIT_UNAVAILABLE: Final = 2

type Kind = Literal["knowledge", "honesty", "persona", "memory", "russian"]


class EvalCase(BaseModel):
    """Строка `eval/qa_ru.jsonl`: реплики пользователя по очереди, проверяется последний ответ."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    kind: Kind
    turns: list[str] = Field(min_length=1)
    expect: Expect


@dataclass(frozen=True, slots=True)
class CaseResult:
    """Итог кейса: последний ответ и найденные проблемы."""

    case_id: str
    kind: str
    reply: str
    problems: tuple[str, ...]

    @property
    def passed(self) -> bool:
        """Кейс пройден, если проблем нет."""
        return not self.problems


async def run_case(llm: LLMPort, case: EvalCase, params: GenerationParams) -> CaseResult:
    """Ведёт диалог по репликам кейса с историей и проверяет последний ответ."""
    history = [Message(Role.SYSTEM, SYSTEM_PROMPT)]
    reply = ""
    for turn in case.turns:
        history.append(Message(Role.USER, turn))
        reply = await collect(llm, tuple(history), params)
        history.append(Message(Role.ASSISTANT, reply))
    return CaseResult(case.id, case.kind, reply, tuple(evaluate(case.expect, reply)))


def render(totals: Counter[str], passed: Counter[str]) -> str:
    """Таблица «категория — пройдено/всего — %» с итоговой строкой."""
    rows = [(kind, passed[kind], totals[kind]) for kind in sorted(totals)]
    rows.append(("Итого", passed.total(), totals.total()))
    lines = [f"{'Категория':<12}{'Пройдено':>10}{'%':>6}"]
    lines += [f"{kind:<12}{f'{ok}/{all_}':>10}{PERCENT * ok // all_:>6}" for kind, ok, all_ in rows]
    return "\n".join(lines)


def load_cases(path: Path) -> list[EvalCase]:
    """Кейсы оценки; ошибка формата — `JsonlError` с номером строки."""
    return read_jsonl(path, EvalCase)


def main(argv: Sequence[str], env: Mapping[str, str], out: TextIO) -> int:
    """Код возврата: 0 — оценка выполнена, 1 — сбой генерации или конфига, 2 — LLM недоступна."""
    args = _parse(argv)
    cases = load_cases(args.cases)
    params = GenerationParams(max_tokens=args.max_tokens, temperature=args.temperature)
    try:
        results = asyncio.run(_run_all(args.backend, env, cases, params))
    except LLMUnavailable as exc:
        print(f"LLM недоступна: {exc}", file=out)
        return EXIT_UNAVAILABLE
    except VtuberError as exc:
        print(f"Оценка прервана: {exc}", file=out)
        return EXIT_FAILED
    totals = Counter(result.kind for result in results)
    passed = Counter(result.kind for result in results if result.passed)
    print(render(totals, passed), file=out)
    for result in (result for result in results if not result.passed):
        print(f"✗ {result.case_id}: {'; '.join(result.problems)}", file=out)
        print(f"    ответ: {result.reply[:REPLY_PREVIEW]!r}", file=out)
    if args.out:
        report = [asdict(result) for result in results]
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


async def _run_all(
    backend: str | None, env: Mapping[str, str], cases: Sequence[EvalCase], params: GenerationParams
) -> list[CaseResult]:
    async with open_llm(backend, env) as llm:
        return [await run_case(llm, case, params) for case in cases]


def _parse(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--backend", help="адаптер из реестра; по умолчанию [llm].backend")
    parser.add_argument("--max-tokens", type=int, default=192)
    parser.add_argument("--temperature", type=float, default=0.3)
    parser.add_argument("--out", type=Path, help="сохранить результаты в JSON")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:], os.environ, sys.stdout))
