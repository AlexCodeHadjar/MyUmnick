"""Цена памяти в TTFT (S-10.5, критерий Этапа 10: p95 +≤ 40 мс): реплики с поиском против без него.

Запуск: `uv run python -m tools.bench_memory [--facts 500] [--runs 3] [--out файл.json]`. Нужны
llama-server (`[llm]`), модель e5 и группа `memory`. Вопросы о пользователе из
`eval/memory_ru.jsonl` идут по кругу: без памяти — обычный промпт, с памятью — настоящий
`MemoryRecall` (e5 + поиск) и справка в реплике; TTFT — от начала хода, как в приложении.
"""

import argparse
import asyncio
import json
import os
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from contextlib import aclosing
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Final, TextIO

from tools.bench_latency import EXIT_UNAVAILABLE, NS_PER_MS, Stats, percentile, render
from tools.eval_memory import DEFAULT_CASES, MemoryCase
from tools.jsonl import read_jsonl
from tools.llm_client import ROOT, open_llm
from vtuber.adapters.memory import E5Embedder, SqliteVecStore
from vtuber.application.memory import MemoryRecall, RecallSearch
from vtuber.application.prompting import PromptBuilder
from vtuber.bootstrap import load_app_config, load_persona
from vtuber.domain import EmbedKind, Fact, FactSource, LLMUnavailable
from vtuber.kernel import EventBus, Telemetry
from vtuber.ports import EmbedderPort, GenerationParams, LLMPort, MemoryStorePort

BATCH: Final = 32
QUANTILES: Final = (0.5, 0.95, 1.0)


@dataclass(frozen=True, slots=True)
class Timing:
    """TTFT одной реплики: без памяти и с ней, мс."""

    ask: str
    plain_ms: float
    with_memory_ms: float


async def first_token_ms(
    llm: LLMPort, prompts: PromptBuilder, ask: str, recall: MemoryRecall | None
) -> float:
    """От начала хода (с поиском, если задан) до первой дельты LLM."""
    started = time.perf_counter_ns()
    context = () if recall is None else (await recall.hints(ask)).context
    messages = prompts.build((), ask, context).messages
    params = GenerationParams(max_tokens=8, temperature=0.3)
    async with aclosing(llm.stream(messages, params)) as stream:
        await anext(stream, None)
    return (time.perf_counter_ns() - started) / NS_PER_MS


async def seed(store: MemoryStorePort, embedder: EmbedderPort, count: int) -> None:
    """Память как после долгого общения: `count` разных фактов."""
    when = datetime.now(UTC)
    for start in range(0, count, BATCH):
        texts = [f"Пользователь упоминал случай номер {i}" for i in range(start, start + BATCH)]
        vectors = await embedder.embed(texts, EmbedKind.PASSAGE)
        for text, vector in zip(texts, vectors, strict=True):
            await store.add(Fact(text, FactSource.EXTRACTED, 0.3, when), vector)


def summarize(timings: Sequence[Timing]) -> dict[str, Stats]:
    """p50/p95/max без памяти и с ней."""
    series = {
        "Без памяти, мс": [t.plain_ms for t in timings],
        "С памятью, мс": [t.with_memory_ms for t in timings],
    }
    return {
        name: Stats(*(percentile(values, q) for q in QUANTILES)) for name, values in series.items()
    }


def memory_cost_ms(timings: Sequence[Timing]) -> float:
    """Цена памяти p50: сравниваются запросы на одном месте в паре, иначе видно только порядок.

    Второй запрос пары быстрее первого на ~100 мс, чей бы он ни был.
    """
    plain_first = [t for index, t in enumerate(timings) if index % 2 == 0]
    memory_first = [t for index, t in enumerate(timings) if index % 2 == 1]
    if not plain_first or not memory_first:
        return 0.0
    first = median(t.with_memory_ms for t in memory_first) - median(t.plain_ms for t in plain_first)
    second = median(t.with_memory_ms for t in plain_first) - median(
        t.plain_ms for t in memory_first
    )
    return (first + second) / 2


def main(argv: Sequence[str], env: Mapping[str, str], out: TextIO) -> int:
    """Код возврата: 0 — готово, 2 — LLM недоступна."""
    args = _parse(argv)
    asks = [case.ask for case in read_jsonl(DEFAULT_CASES, MemoryCase)]
    try:
        timings = asyncio.run(_bench(args, env, asks))
    except LLMUnavailable as exc:
        print(f"LLM недоступна: {exc}", file=out)
        return EXIT_UNAVAILABLE
    summary = summarize(timings)
    print(render(summary, len(timings)), file=out)
    print(f"Цена памяти p50 на одном месте в паре: {memory_cost_ms(timings):+.1f} мс", file=out)
    if args.out:
        report = {"summary": summary, "timings": timings}
        args.out.write_text(
            json.dumps(report, default=asdict, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return 0


async def _bench(
    args: argparse.Namespace, env: Mapping[str, str], asks: Sequence[str]
) -> list[Timing]:
    cfg = load_app_config(ROOT, env)
    memory = cfg.memory.resolved(ROOT)
    prompts = PromptBuilder(load_persona(ROOT / cfg.persona.file))
    timings = []
    with tempfile.TemporaryDirectory() as tmp:
        async with (
            open_llm(args.backend, env) as llm,
            E5Embedder(memory.e5) as embedder,
            SqliteVecStore(Path(tmp) / "memory.sqlite", memory.e5.dimensions) as store,
        ):
            await seed(store, embedder, args.facts)
            recall = MemoryRecall(
                RecallSearch(embedder, store), memory.retrieval, Telemetry(EventBus())
            )
            for index, ask in enumerate([*asks] * args.runs):
                timings.append(await _pair(llm, prompts, ask, recall, memory_first=index % 2 == 1))
    return timings


async def _pair(
    llm: LLMPort, prompts: PromptBuilder, ask: str, recall: MemoryRecall, *, memory_first: bool
) -> Timing:
    """Порядок чередуется: при постоянном (2026-11-03) память незаслуженно выигрывала 100 мс."""
    if memory_first:
        with_memory = await first_token_ms(llm, prompts, ask, recall)
        return Timing(ask, await first_token_ms(llm, prompts, ask, None), with_memory)
    plain = await first_token_ms(llm, prompts, ask, None)
    return Timing(ask, plain, await first_token_ms(llm, prompts, ask, recall))


def _parse(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--facts", type=int, default=500, help="сколько фактов в памяти")
    parser.add_argument("--runs", type=int, default=3, help="кругов по вопросам")
    parser.add_argument("--backend", help="адаптер из реестра; по умолчанию [llm].backend")
    parser.add_argument("--out", type=Path, help="сохранить замеры в JSON")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:], os.environ, sys.stdout))
