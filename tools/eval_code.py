"""Качество модели для кода (S-12.5): задача → ответ модели → настоящий запуск с проверками.

Запуск: `uv run python -m tools.eval_code [--cases eval/code_en.jsonl] [--url http://127.0.0.1:8081]`.
Запускает код, который написала модель: только на арендованной машине или в песочнице. Каждая
задача — в своём процессе и пустой папке, с изолированным интерпретатором и сроком.
"""

import argparse
import asyncio
import json
import re
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from contextlib import aclosing
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Final, TextIO

from pydantic import BaseModel, ConfigDict, Field

from tools.jsonl import read_jsonl
from tools.llm_client import ROOT
from vtuber.adapters.llm import LLMConfig, OpenAICompatLLM
from vtuber.domain import LLMUnavailable, Message, Role, VtuberError
from vtuber.ports import GenerationParams, LLMPort

DEFAULT_CASES: Final = ROOT / "eval" / "code_en.jsonl"
RUN_TIMEOUT_S: Final = 10.0
PERCENT: Final = 100
MS_PER_S: Final = 1000
EXIT_FAILED: Final = 1
EXIT_UNAVAILABLE: Final = 2
_FENCE: Final = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
_SYSTEM: Final = "You are a senior programmer. Reply with one Python code block and nothing else."


class CodeCase(BaseModel):
    """Строка набора: задача на английском и проверки, которые код должен пройти."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    task: str = Field(min_length=1)
    checks: str = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class CodeResult:
    """Итог задачи; `problem` — почему не прошла."""

    case_id: str
    passed: bool
    problem: str = ""
    ttft_ms: float = 0.0
    total_ms: float = 0.0


def extract_code(reply: str) -> str:
    """Первый блок кода; без блока — весь ответ: иначе модель зря получила бы ноль за формат."""
    match = _FENCE.search(reply)
    return match.group(1) if match else reply


def run_checks(code: str, checks: str, timeout_s: float = RUN_TIMEOUT_S) -> str:
    """Пустая строка — прошло; иначе причина. `-I`: чужой код не подхватит файлы из папки."""
    with tempfile.TemporaryDirectory() as folder:
        script = Path(folder) / "candidate.py"
        script.write_text(f"{code}\n\n{checks}\n", encoding="utf-8")
        try:
            done = subprocess.run(  # noqa: S603 — запуск кода модели и есть цель инструмента
                [sys.executable, "-I", str(script)],
                cwd=folder,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return f"не уложился в {timeout_s:.0f} с"
    return "" if done.returncode == 0 else done.stderr.strip().splitlines()[-1][:200]


def judge(case: CodeCase, reply: str) -> CodeResult:
    """Ответ модели → запуск с проверками задачи."""
    problem = run_checks(extract_code(reply), case.checks)
    return CodeResult(case.id, not problem, problem)


def render(results: Sequence[CodeResult]) -> str:
    """Итог и непрошедшие задачи."""
    passed = sum(r.passed for r in results)
    share = PERCENT * passed / max(len(results), 1)
    ttft = sum(r.ttft_ms for r in results) / max(len(results), 1)
    lines = [
        f"Задач: {len(results)}; прошло: {passed} ({share:.0f} %); TTFT в среднем {ttft:.0f} мс"
    ]
    lines += [f"x {r.case_id}: {r.problem}" for r in results if not r.passed]
    return "\n".join(lines)


async def _timed(
    llm: LLMPort, messages: Sequence[Message], params: GenerationParams
) -> tuple[str, float, float]:
    started = time.perf_counter()
    first: float | None = None
    parts = []
    async with aclosing(llm.stream(messages, params)) as deltas:
        async for delta in deltas:
            first = first if first is not None else time.perf_counter()
            parts.append(delta)
    ended = time.perf_counter()
    return "".join(parts), ((first or ended) - started) * MS_PER_S, (ended - started) * MS_PER_S


async def run_cases(
    llm: LLMPort, cases: Sequence[CodeCase], params: GenerationParams
) -> list[CodeResult]:
    """Каждая задача — отдельный разговор; запуск в потоке, чтобы не держать цикл событий."""
    results = []
    for case in cases:
        messages = [Message(Role.SYSTEM, _SYSTEM), Message(Role.USER, case.task)]
        reply, ttft_ms, total_ms = await _timed(llm, messages, params)
        verdict = await asyncio.to_thread(judge, case, reply)
        results.append(replace(verdict, ttft_ms=ttft_ms, total_ms=total_ms))
    return results


async def _bench(url: str, cases: Sequence[CodeCase]) -> list[CodeResult]:
    cfg = LLMConfig.model_validate(
        {
            "backend": "openai_compat",
            "base_url": url,
            "model": "code",
            "connect_timeout_s": 5.0,
            "read_timeout_s": 300.0,
            "generation": {"max_tokens": 1024, "temperature": 0.0},
            "llamacpp": {
                "slot_id": 0,
                "enable_thinking": False,
                "forbid_foreign_scripts": False,
                "forbid_cyrillic": False,
            },
        }
    )
    async with OpenAICompatLLM(cfg) as llm:
        return await run_cases(llm, cases, GenerationParams(max_tokens=1024, temperature=0.0))


def main(argv: Sequence[str], out: TextIO) -> int:
    """Код возврата: 0 — готово, 1 — сбой генерации, 2 — модель недоступна."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--url", default="http://127.0.0.1:8081")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        results = asyncio.run(_bench(args.url, read_jsonl(args.cases, CodeCase)))
    except LLMUnavailable as exc:
        print(f"Модель недоступна: {exc}", file=out)
        return EXIT_UNAVAILABLE
    except VtuberError as exc:
        print(f"Оценка прервана: {exc}", file=out)
        return EXIT_FAILED
    print(render(results), file=out)
    if args.out:
        text = json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=1)
        args.out.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:], sys.stdout))
