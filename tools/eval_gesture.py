"""Оценка жестов на настоящей модели (S-18.4): уместность, частота, утечки в текст.

Запуск: `uv run python -m tools.eval_gesture [--cases eval/gesture_ru.jsonl] [--runs 1]
[--temperature 0.7]`. Сервер и адрес — из `[llm]`, промпт — настоящей персоны, разбор — настоящий
`StreamParser`. Ответ без жеста не ошибка: жест уместен не всегда, поэтому считается отдельно.
"""

import argparse
import asyncio
import os
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TextIO

from pydantic import BaseModel, ConfigDict, Field

from tools.jsonl import read_jsonl
from tools.llm_client import ROOT, collect, open_llm
from vtuber.application.pipeline import GestureCue, StreamParser, TextDelta
from vtuber.application.prompting import PromptBuilder
from vtuber.bootstrap import load_app_config, load_persona
from vtuber.domain import Gesture, LLMUnavailable, VtuberError
from vtuber.ports import GenerationParams, LLMPort

DEFAULT_CASES: Final = ROOT / "eval" / "gesture_ru.jsonl"
PERCENT: Final = 100
EXIT_FAILED: Final = 1
EXIT_UNAVAILABLE: Final = 2
_LEAK: Final = re.compile(r"</?\s*[A-Za-z_]+\s*>|\[/?[A-Za-z_]+\]")


class GestureCase(BaseModel):
    """Строка набора: реплика и жесты, уместные в ответе на неё."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    text: str = Field(min_length=1)
    fits: tuple[Gesture, ...] = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class GestureResult:
    """Разбор одного ответа; `fitting` — все жесты ответа уместны (нет жестов — тоже)."""

    case_id: str
    reply: str
    gestures: tuple[Gesture, ...]
    fitting: bool
    leaked: tuple[str, ...]


def judge(case: GestureCase, reply: str) -> GestureResult:
    """Разбирает ответ настоящим `StreamParser` — как в ходе, без отдельных правил."""
    parser = StreamParser()
    events = [*parser.feed(reply), *parser.flush()]
    gestures = tuple(event.gesture for event in events if isinstance(event, GestureCue))
    shown = "".join(event.text for event in events if isinstance(event, TextDelta))
    fitting = all(gesture in case.fits for gesture in gestures)
    return GestureResult(case.id, reply, gestures, fitting, tuple(_LEAK.findall(shown)))


def render(results: Sequence[GestureResult]) -> str:
    """Итог и все непрошедшие ответы."""
    gestured = [r for r in results if r.gestures]
    fitting = sum(r.fitting for r in gestured)
    share = PERCENT * len(gestured) / max(len(results), 1)
    fit_share = PERCENT * fitting / max(len(gestured), 1)
    leaked = sum(bool(r.leaked) for r in results)
    lines = [
        (
            f"Ответов: {len(results)}; с жестом: {len(gestured)} ({share:.0f} %); "
            f"уместных из них: {fitting} ({fit_share:.0f} %); утечек: {leaked}"
        )
    ]
    lines += [
        f"x {r.case_id}: {[g.value for g in r.gestures]} | {r.leaked} | {r.reply[:100]!r}"
        for r in results
        if not r.fitting or r.leaked
    ]
    return "\n".join(lines)


async def run_cases(
    llm: LLMPort, prompts: PromptBuilder, cases: Sequence[GestureCase], params: GenerationParams
) -> list[GestureResult]:
    """Каждая реплика — отдельный разговор: история не подсказывает жест."""
    results = []
    for case in cases:
        reply = await collect(llm, prompts.build((), case.text).messages, params)
        results.append(judge(case, reply))
    return results


def main(argv: Sequence[str], env: Mapping[str, str], out: TextIO) -> int:
    """Код возврата: 0 — готово, 1 — сбой генерации или конфига, 2 — LLM недоступна."""
    args = _parse(argv)
    cases = read_jsonl(args.cases, GestureCase) * args.runs
    try:
        results = asyncio.run(_bench(args, env, cases))
    except LLMUnavailable as exc:
        print(f"LLM недоступна: {exc}", file=out)
        return EXIT_UNAVAILABLE
    except VtuberError as exc:
        print(f"Оценка прервана: {exc}", file=out)
        return EXIT_FAILED
    print(render(results), file=out)
    return 0


async def _bench(
    args: argparse.Namespace, env: Mapping[str, str], cases: Sequence[GestureCase]
) -> list[GestureResult]:
    cfg = load_app_config(ROOT, env)
    prompts = PromptBuilder(load_persona(ROOT / cfg.persona.file))
    params = GenerationParams(max_tokens=128, temperature=args.temperature)
    async with open_llm(None, env) as llm:
        return await run_cases(llm, prompts, cases, params)


def _parse(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--runs", type=int, default=1, help="кругов по всем репликам")
    parser.add_argument("--temperature", type=float, default=0.7)
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:], os.environ, sys.stdout))
