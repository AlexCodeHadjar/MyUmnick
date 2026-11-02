"""Сквозная проверка долговременной памяти (Этап 10): факт из одного разговора — в ответе другого.

Запуск: `uv run python -m tools.eval_memory [--cases eval/memory_ru.jsonl] [--out отчёт.json]`.
Нужны llama-server (`[llm]`), модель e5 и группа `memory`. Первый «сеанс» — реплики пользователя,
ответы модели и настоящее извлечение фактов (`FactMemory.learn`) в отдельную временную базу на кейс;
второй — пустая история, только настоящий гейт поиска, справка и вопрос. Критерий Этапа 10:
факт используется в ответе. `--out` хранит факты и ответы — для записанных тестов.
"""

import argparse
import asyncio
import json
import os
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, TextIO

from pydantic import BaseModel, ConfigDict, Field

from tools.eval_checks import Expect, evaluate
from tools.jsonl import read_jsonl
from tools.llm_client import ROOT, collect, open_llm
from vtuber.adapters.memory import SqliteVecStore
from vtuber.application.memory import FactExtractor, FactMemory, MemoryRecall
from vtuber.application.prompting import PromptBuilder
from vtuber.bootstrap import load_app_config, load_persona
from vtuber.domain import GenerationFailed, LLMUnavailable, Turn, TurnId, VtuberError
from vtuber.kernel import EventBus, Telemetry
from vtuber.ports import EmbedderPort, GenerationParams, LLMPort, MemoryStorePort

DEFAULT_CASES: Final = ROOT / "eval" / "memory_ru.jsonl"
PERCENT: Final = 100
EXIT_FAILED: Final = 1
EXIT_UNAVAILABLE: Final = 2


class MemoryCase(BaseModel):
    """Строка набора: что пользователь рассказал в первом сеансе и о чём спросил во втором."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    say: tuple[str, ...] = Field(min_length=1)
    ask: str = Field(min_length=1)
    expect: Expect


@dataclass(frozen=True, slots=True)
class MemoryResult:
    """Итог кейса: сколько фактов записано, дошла ли справка, что ответила модель."""

    case_id: str
    stored: int
    extraction_failures: int
    context: tuple[str, ...]
    reply: str
    problems: tuple[str, ...]

    @property
    def passed(self) -> bool:
        """Факт дошёл до ответа."""
        return not self.problems


@dataclass(frozen=True, slots=True)
class Engines:
    """Настоящие части памяти: LLM, эмбеддер и сборка промпта; база — своя на каждый кейс."""

    llm: LLMPort
    embedder: EmbedderPort
    prompts: PromptBuilder
    reply_params: GenerationParams


async def run_case(engines: Engines, case: MemoryCase, store: MemoryStorePort) -> MemoryResult:
    """Первый сеанс в `store`, затем новый разговор с пустой историей."""
    cfg = load_app_config(ROOT, {}).memory
    extractor = FactExtractor(engines.llm, engines.reply_params)
    facts = FactMemory(extractor, engines.embedder, store, cfg.facts)
    stored, failures = 0, 0
    for number, line in enumerate(case.say, start=1):
        messages = engines.prompts.build((), line).messages
        reply = await collect(engines.llm, messages, engines.reply_params)
        try:
            stored += await facts.learn(Turn(TurnId(number), line, reply), datetime.now(UTC))
        except GenerationFailed:
            failures += 1
    telemetry = Telemetry(EventBus())
    hints = await MemoryRecall(engines.embedder, store, cfg.retrieval, telemetry).hints(case.ask)
    prompt = engines.prompts.build((), case.ask, hints.context)
    answer = await collect(engines.llm, prompt.messages, engines.reply_params)
    problems = tuple(evaluate(case.expect, answer))
    return MemoryResult(case.id, stored, failures, hints.context, answer, problems)


def render(results: Sequence[MemoryResult]) -> str:
    """Итог по этапам: факт записан, справка дошла, ответ верный; непрошедшие — списком."""
    total = len(results)
    stored = sum(r.stored > 0 for r in results)
    recalled = sum(bool(r.context) for r in results)
    passed = sum(r.passed for r in results)
    lines = [
        (
            f"Кейсов: {total}; факт записан: {stored}; справка дошла: {recalled}; "
            f"ответ верный: {passed} ({PERCENT * passed / total:.0f} %)"
        )
    ]
    lines += [
        f"x {r.case_id}: записано {r.stored}, сбоев {r.extraction_failures}, "
        f"справка {r.context}; {r.reply[:100]!r}"
        for r in results
        if not r.passed
    ]
    return "\n".join(lines)


def main(argv: Sequence[str], env: Mapping[str, str], out: TextIO) -> int:
    """Код возврата: 0 — готово, 1 — сбой конфига или генерации, 2 — LLM недоступна."""
    args = _parse(argv)
    cases = read_jsonl(args.cases, MemoryCase)
    try:
        results = asyncio.run(_run_all(args, env, cases))
    except LLMUnavailable as exc:
        print(f"LLM недоступна: {exc}", file=out)
        return EXIT_UNAVAILABLE
    except VtuberError as exc:
        print(f"Оценка прервана: {exc}", file=out)
        return EXIT_FAILED
    print(render(results), file=out)
    if args.out:
        text = json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=1)
        args.out.write_text(text + "\n", encoding="utf-8")
    return 0


async def _run_all(
    args: argparse.Namespace, env: Mapping[str, str], cases: Sequence[MemoryCase]
) -> list[MemoryResult]:
    from vtuber.adapters.memory import E5Embedder  # noqa: PLC0415 — грузит модель только здесь

    cfg = load_app_config(ROOT, env)
    memory = cfg.memory.resolved(ROOT)
    prompts = PromptBuilder(load_persona(ROOT / cfg.persona.file))
    params = GenerationParams(max_tokens=args.max_tokens, temperature=args.temperature)
    results = []
    async with open_llm(args.backend, env) as llm, E5Embedder(memory.e5) as embedder:
        engines = Engines(llm, embedder, prompts, params)
        for case in cases:
            with tempfile.TemporaryDirectory() as tmp:
                db = Path(tmp) / "memory.sqlite"
                async with SqliteVecStore(db, memory.e5.dimensions) as store:
                    results.append(await run_case(engines, case, store))
    return results


def _parse(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--backend", help="адаптер из реестра; по умолчанию [llm].backend")
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.3)
    parser.add_argument("--out", type=Path, help="сохранить факты и ответы в JSON")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:], os.environ, sys.stdout))
