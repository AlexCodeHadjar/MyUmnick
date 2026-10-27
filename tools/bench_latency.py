"""Бенчмарк задержки LLM: TTFT, ответ целиком и TPS по эталонным репликам (p50/p95/max).

Запуск: `uv run python -m tools.bench_latency [--runs 3] [--backend llamacpp] [--out файл.json]`.
Сервер и адрес — из `[llm]` конфига (`scripts/start_llm.ps1`). Методика — docs/performance.md.
"""

import argparse
import asyncio
import json
import math
import os
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Literal, TextIO

from pydantic import BaseModel, ConfigDict

from tools.jsonl import read_jsonl
from tools.llm_client import ROOT, SYSTEM_PROMPT, open_llm
from vtuber.domain import LLMUnavailable, Message, Role, VtuberError
from vtuber.ports import GenerationParams, LLMPort

DEFAULT_PROMPTS: Final = ROOT / "bench" / "prompts_ru.jsonl"
WARMUP_TEXT: Final = "Привет!"
NS_PER_MS: Final = 1_000_000
MS_PER_S: Final = 1000
QUANTILES: Final = (("p50", 0.5), ("p95", 0.95), ("max", 1.0))
EXIT_FAILED: Final = 1
EXIT_UNAVAILABLE: Final = 2


class BenchPrompt(BaseModel):
    """Строка `bench/prompts_ru.jsonl`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    kind: Literal["short", "medium", "long", "memory"]
    text: str


@dataclass(frozen=True, slots=True)
class Sample:
    """Один замер ответа."""

    prompt_id: str
    ttft_ms: float
    total_ms: float
    deltas: int

    @property
    def tps(self) -> float:
        """Дельт в секунду после первой; у llama-server одна дельта ≈ один токен."""
        generation_s = (self.total_ms - self.ttft_ms) / MS_PER_S
        if self.deltas < 2 or generation_s <= 0:  # noqa: PLR2004 — нужна хотя бы пара дельт
            return 0.0
        return (self.deltas - 1) / generation_s


@dataclass(frozen=True, slots=True)
class Stats:
    """Распределение метрики."""

    p50: float
    p95: float
    max: float


def percentile(values: Sequence[float], q: float) -> float:
    """Перцентиль методом ближайшего ранга: без интерполяции, устойчив на малых выборках."""
    ordered = sorted(values)
    rank = max(1, math.ceil(q * len(ordered)))
    return ordered[rank - 1]


async def measure(
    llm: LLMPort,
    prompt: BenchPrompt,
    params: GenerationParams,
    clock: Callable[[], int] = time.perf_counter_ns,
) -> Sample:
    """Замеряет один ответ на реплику `prompt` после системного промпта."""
    messages = (Message(Role.SYSTEM, SYSTEM_PROMPT), Message(Role.USER, prompt.text))
    started, first, deltas = clock(), 0, 0
    async for _ in llm.stream(messages, params):
        first = first or clock()
        deltas += 1
    finished = clock()
    first = first or finished
    return Sample(
        prompt.id, (first - started) / NS_PER_MS, (finished - started) / NS_PER_MS, deltas
    )


async def run_bench(
    llm: LLMPort, prompts: Sequence[BenchPrompt], params: GenerationParams, runs: int
) -> list[Sample]:
    """Прогрев (T-06), затем `runs` кругов по всем репликам.

    По кругу, а не каждая реплика подряд: повтор той же реплики целиком попал бы в KV-кэш и
    дал бы нереально низкий TTFT. В кэше остаётся только общий системный промпт — как в жизни.
    """
    await llm.prefill((Message(Role.SYSTEM, SYSTEM_PROMPT),))
    await measure(llm, BenchPrompt(id="warmup", kind="short", text=WARMUP_TEXT), params)
    return [await measure(llm, prompt, params) for _ in range(runs) for prompt in prompts]


def summarize(samples: Sequence[Sample]) -> dict[str, Stats]:
    """p50/p95/max по TTFT, полному ответу и TPS."""
    metrics = {
        "TTFT, мс": [sample.ttft_ms for sample in samples],
        "Ответ целиком, мс": [sample.total_ms for sample in samples],
        "TPS": [sample.tps for sample in samples],
    }
    return {
        name: Stats(*(percentile(values, q) for _, q in QUANTILES))
        for name, values in metrics.items()
    }


def render(summary: Mapping[str, Stats], count: int) -> str:
    """Таблица для консоли."""
    header = f"{'Метрика':<20}" + "".join(f"{name:>10}" for name, _ in QUANTILES)
    rows = [
        f"{name:<20}{stats.p50:>10.1f}{stats.p95:>10.1f}{stats.max:>10.1f}"
        for name, stats in summary.items()
    ]
    return "\n".join([header, *rows, f"Замеров: {count}"])


def load_prompts(path: Path) -> list[BenchPrompt]:
    """Реплики бенчмарка; ошибка формата — `JsonlError` с номером строки."""
    return read_jsonl(path, BenchPrompt)


def main(argv: Sequence[str], env: Mapping[str, str], out: TextIO) -> int:
    """Код возврата: 0 — готово, 1 — сбой генерации или конфига, 2 — LLM-сервер недоступен."""
    args = _parse(argv)
    prompts = load_prompts(args.prompts)
    params = GenerationParams(max_tokens=args.max_tokens, temperature=args.temperature)
    try:
        samples = asyncio.run(_bench(args.backend, env, prompts, params, args.runs))
    except LLMUnavailable as exc:
        print(f"LLM недоступна: {exc}", file=out)
        return EXIT_UNAVAILABLE
    except VtuberError as exc:
        print(f"Бенчмарк прерван: {exc}", file=out)
        return EXIT_FAILED
    summary = summarize(samples)
    print(render(summary, len(samples)), file=out)
    if args.out:
        report = {"summary": {k: asdict(v) for k, v in summary.items()}, "samples": samples}
        text = json.dumps(report, default=asdict, ensure_ascii=False, indent=2)
        args.out.write_text(text, encoding="utf-8")
    return 0


async def _bench(
    backend: str | None,
    env: Mapping[str, str],
    prompts: Sequence[BenchPrompt],
    params: GenerationParams,
    runs: int,
) -> list[Sample]:
    async with open_llm(backend, env) as llm:
        return await run_bench(llm, prompts, params, runs)


def _parse(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompts", type=Path, default=DEFAULT_PROMPTS)
    parser.add_argument("--runs", type=int, default=3, help="кругов по всем репликам")
    parser.add_argument("--backend", help="адаптер из реестра; по умолчанию [llm].backend")
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--out", type=Path, help="сохранить замеры в JSON")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:], os.environ, sys.stdout))
