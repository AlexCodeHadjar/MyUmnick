"""Цена нашего кода в ходе и поиск блокировок цикла событий (S-9.1, S-9.4): без GPU и без сервера.

Запуск: `uv run python -m tools.bench_core [--turns 200] [--out отчёт.json] [--inject-delay-ms 0]`.
LLM — заглушка без задержки, поэтому цифры — только промпт, разбор, шлюз и кодек, а не бюджет TTFT.
Сначала замер, затем второй проход в отладочном режиме asyncio: он замедляет код, зато называет
колбэки дольше `SLOW_CALLBACK_S`. `--inject-delay-ms` — искусственная регрессия для проверки гейта.
"""

import argparse
import asyncio
import json
import logging
import os
import platform
import sys
import time
from collections.abc import AsyncGenerator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, TextIO

from tools.bench_latency import percentile
from tools.bench_voice import CHARS_PER_TOKEN, SCRIPTED_REPLIES
from tools.llm_client import ROOT
from vtuber.application.conversation import ConversationService
from vtuber.application.memory import ShortTermMemory
from vtuber.application.pipeline import ReplyPipeline
from vtuber.application.prompting import ContextBudget, ContextConfig, PromptBuilder
from vtuber.bootstrap import load_app_config, load_persona
from vtuber.domain import Message
from vtuber.gateway import ChatDelta, OutboundMessage, WsReplySink
from vtuber.gateway.codec import encode_outbound
from vtuber.kernel import EventBus, Telemetry
from vtuber.ports import GenerationParams

# Выше шага часов Windows (~15,6 мс): меньший порог срабатывает на любом колбэке, попавшем на тик.
SLOW_CALLBACK_S: Final = 0.05
MS_PER_S: Final = 1000
P50: Final = 0.5
P95: Final = 0.95
USER_TEXT: Final = "Расскажи коротко, как прошёл твой день и что нового ты узнала."
BLOCKING_PREFIX: Final = "Executing "


class _InstantLLM:
    """LLM без ожидания: таймер Windows округляет любой сон до ~15 мс и замер мерил бы его."""

    def __init__(self) -> None:
        self._count = 0

    async def stream(
        self, messages: Sequence[Message], params: GenerationParams
    ) -> AsyncGenerator[str]:
        """Ответ кусками; между ними цикл событий свободен, как при настоящем потоке."""
        del messages, params
        reply = SCRIPTED_REPLIES[self._count % len(SCRIPTED_REPLIES)]
        self._count += 1
        for start in range(0, len(reply), CHARS_PER_TOKEN):
            yield reply[start : start + CHARS_PER_TOKEN]
            await asyncio.sleep(0)

    async def prefill(self, messages: Sequence[Message]) -> None:
        """Кэша нет."""
        del messages
        await asyncio.sleep(0)


@dataclass(slots=True)
class _Timing:
    """Замер одного хода; шлёт как шлюз: кодек — часть пути."""

    delay_s: float = 0.0
    started: float = 0.0
    first_text: float | None = None

    async def send(self, message: OutboundMessage) -> None:
        encode_outbound(message)
        if isinstance(message, ChatDelta) and self.first_text is None:
            if self.delay_s > 0:
                await asyncio.sleep(self.delay_s)
            self.first_text = time.perf_counter()

    async def send_bytes(self, frame: bytes) -> None:
        del frame
        await asyncio.sleep(0)


@dataclass(slots=True)
class _Slow(logging.Handler):
    """Сообщения asyncio о колбэках дольше порога."""

    found: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        logging.Handler.__init__(self)

    def __hash__(self) -> int:
        return id(self)

    def emit(self, record: logging.LogRecord) -> None:
        text = record.getMessage()
        if text.startswith(BLOCKING_PREFIX):
            self.found.append(text)


def _service(env: Mapping[str, str]) -> ConversationService:
    cfg = load_app_config(ROOT, env)
    bus = EventBus()
    pipeline = ReplyPipeline(
        _InstantLLM(),
        GenerationParams(max_tokens=128, temperature=0.7),
        Telemetry(bus),
    )
    budget = ContextBudget(
        ContextConfig(
            max_history_tokens=2000, trim_ratio=0.5, chars_per_token=3, message_overhead_tokens=4
        )
    )
    prompts = PromptBuilder(load_persona(ROOT / cfg.persona.file))
    return ConversationService(pipeline, prompts, ShortTermMemory(budget), bus)


async def _measure(turns: int, delay_s: float, env: Mapping[str, str]) -> dict[str, list[float]]:
    service = _service(env)
    first: list[float] = []
    whole: list[float] = []
    for _ in range(turns):
        timing = _Timing(delay_s=delay_s, started=time.perf_counter())
        await service.handle(USER_TEXT, WsReplySink(timing.send, timing.send_bytes))
        await service.wait_idle()
        ended = time.perf_counter()
        if timing.first_text is not None:
            first.append((timing.first_text - timing.started) * MS_PER_S)
        whole.append((ended - timing.started) * MS_PER_S)
    return {"core.first_text_ms": first, "core.turn_ms": whole}


async def _scan(turns: int, env: Mapping[str, str]) -> None:
    asyncio.get_running_loop().slow_callback_duration = SLOW_CALLBACK_S
    await _measure(turns, 0.0, env)


def find_blocking(turns: int, env: Mapping[str, str]) -> list[str]:
    """Отладочный проход: что держало цикл событий дольше порога."""
    logger = logging.getLogger("asyncio")
    handler = _Slow()
    logger.addHandler(handler)
    try:
        asyncio.run(_scan(turns, env), debug=True)
    finally:
        logger.removeHandler(handler)
    return handler.found


def report(samples: Mapping[str, Sequence[float]], blocking: Sequence[str]) -> dict[str, object]:
    """Отчёт для `tools.perf_gate`; машина — чтобы не сравнивать чужие цифры."""
    metrics = {
        name: {"p50": percentile(values, P50), "p95": percentile(values, P95)}
        for name, values in samples.items()
    }
    machine = f"{platform.node()} {platform.processor()}"
    return {"machine": machine, "metrics": metrics, "blocking": list(blocking)}


def main(argv: Sequence[str], env: Mapping[str, str], out: TextIO) -> int:
    """Печатает отчёт; `--out` сохраняет его для гейта."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--turns", type=int, default=200)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--inject-delay-ms", type=float, default=0.0)
    args = parser.parse_args(argv)
    samples = asyncio.run(_measure(args.turns, args.inject_delay_ms / MS_PER_S, env))
    text = json.dumps(report(samples, find_blocking(args.turns, env)), ensure_ascii=False, indent=1)
    print(text, file=out)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:], os.environ, sys.stdout))
