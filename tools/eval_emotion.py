"""Оценка тегов эмоций на настоящей модели (S-8.1): тег есть, уместен, не попал в текст и речь.

Запуск: `uv run python -m tools.eval_emotion [--cases eval/emotion_ru.jsonl] [--runs 1]
[--temperature 0.7] [--out отчёт.json]`. Сервер и адрес — из `[llm]`, промпт — настоящей персоны.
Ответы проходят через настоящий `StreamParser`; `--out` хранит сырые ответы — из них берутся
записанные ответы для тестов разбора. Критерий Этапа 8: тег есть и уместен в ≥ 85 %.
"""

import argparse
import asyncio
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, TextIO

from pydantic import BaseModel, ConfigDict, Field

from tools.jsonl import read_jsonl
from tools.llm_client import ROOT, collect, open_llm
from vtuber.application.pipeline import EmotionCue, StreamParser, TextDelta
from vtuber.application.prompting import PromptBuilder
from vtuber.bootstrap import load_app_config, load_persona
from vtuber.domain import Emotion, LLMUnavailable, VtuberError
from vtuber.ports import GenerationParams, LLMPort

DEFAULT_CASES: Final = ROOT / "eval" / "emotion_ru.jsonl"
PERCENT: Final = 100
EXIT_FAILED: Final = 1
EXIT_UNAVAILABLE: Final = 2
# Всё, что похоже на тег, в показанном тексте: разметка не должна доходить до чата и голоса.
_LEAK: Final = re.compile(r"</?\s*[A-Za-z_]+\s*>|\[/?[A-Za-z_]+\]")


class EmotionCase(BaseModel):
    """Строка набора: реплика и эмоции, с которых уместно начать ответ."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    text: str = Field(min_length=1)
    fits: tuple[Emotion, ...] = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class EmotionResult:
    """Разбор одного ответа; `tagged` — тег в самом начале, `fitting` — первая эмоция уместна."""

    case_id: str
    reply: str
    shown: str
    emotions: tuple[Emotion, ...]
    tagged: bool
    fitting: bool
    leaked: tuple[str, ...]


def judge(case: EmotionCase, reply: str) -> EmotionResult:
    """Разбирает ответ настоящим `StreamParser` — как в ходе, без отдельных правил."""
    parser = StreamParser()
    events = [*parser.feed(reply), *parser.flush()]
    emotions = tuple(event.emotion for event in events if isinstance(event, EmotionCue))
    shown = "".join(event.text for event in events if isinstance(event, TextDelta))
    first_is_cue = bool(events) and isinstance(events[0], EmotionCue)
    return EmotionResult(
        case.id,
        reply,
        shown,
        emotions,
        tagged=first_is_cue,
        fitting=first_is_cue and emotions[0] in case.fits,
        leaked=tuple(_LEAK.findall(shown)),
    )


def render(results: Sequence[EmotionResult]) -> str:
    """Итог и все непрошедшие ответы."""
    total = len(results)
    tagged = sum(r.tagged for r in results)
    fitting = sum(r.fitting for r in results)
    leaked = sum(bool(r.leaked) for r in results)
    lines = [
        (
            f"Ответов: {total}; с тегом в начале: {tagged} ({PERCENT * tagged / total:.0f} %); "
            f"тег уместен: {fitting} ({PERCENT * fitting / total:.0f} %); утечек: {leaked}"
        ),
    ]
    lines += [
        f"x {r.case_id}: {[e.value for e in r.emotions]} | {r.leaked} | {r.reply[:100]!r}"
        for r in results
        if not r.fitting or r.leaked
    ]
    return "\n".join(lines)


async def run_cases(
    llm: LLMPort, prompts: PromptBuilder, cases: Sequence[EmotionCase], params: GenerationParams
) -> list[EmotionResult]:
    """Каждая реплика — отдельный разговор: история не подсказывает настроение."""
    results = []
    for case in cases:
        reply = await collect(llm, prompts.build((), case.text).messages, params)
        results.append(judge(case, reply))
    return results


def main(argv: Sequence[str], env: Mapping[str, str], out: TextIO) -> int:
    """Код возврата: 0 — готово, 1 — сбой генерации или конфига, 2 — LLM недоступна."""
    args = _parse(argv)
    cases = read_jsonl(args.cases, EmotionCase) * args.runs
    try:
        results = asyncio.run(_bench(args, env, cases))
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


async def _bench(
    args: argparse.Namespace, env: Mapping[str, str], cases: Sequence[EmotionCase]
) -> list[EmotionResult]:
    cfg = load_app_config(ROOT, env)
    prompts = PromptBuilder(load_persona(ROOT / (args.persona or cfg.persona.file)))
    params = GenerationParams(max_tokens=args.max_tokens, temperature=args.temperature)
    async with open_llm(args.backend, env) as llm:
        return await run_cases(llm, prompts, cases, params)


def _parse(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--runs", type=int, default=1, help="кругов по всем репликам")
    parser.add_argument("--persona", help="файл персоны от корня; по умолчанию [persona].file")
    parser.add_argument("--backend", help="адаптер из реестра; по умолчанию [llm].backend")
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--out", type=Path, help="сохранить ответы в JSON")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:], os.environ, sys.stdout))
