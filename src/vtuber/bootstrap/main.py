"""Точка входа: `python -m vtuber` — чат в терминале (M1), `python -m vtuber serve` — шлюз UI."""

import argparse
import asyncio
import os
import sys
from collections.abc import Mapping, Sequence
from contextlib import ExitStack
from pathlib import Path
from typing import Final, Protocol, TextIO

from vtuber.application.conversation import ConversationService
from vtuber.bootstrap.config import AppConfig, load_app_config
from vtuber.bootstrap.container import Core, build_conversation, llm_backends
from vtuber.bootstrap.persona import load_persona
from vtuber.domain import (
    BackendState,
    BackendStatusChanged,
    Component,
    ConfigError,
    LLMUnavailable,
    Message,
    MetricRecorded,
    Persona,
)
from vtuber.gateway import GatewayServer, TerminalChat
from vtuber.kernel import EventBus, Telemetry, TraceWriter, get_logger, logging_to
from vtuber.ports import LLMPort

EXIT_CONFIG: Final = 1
EXIT_UNAVAILABLE: Final = 2
CHAT_MODE: Final = "chat"
SERVE_MODE: Final = "serve"

_log = get_logger(__name__)


class LineSource(Protocol):
    """Откуда читать строки: `sys.stdin` или его тестовая замена."""

    def readline(self) -> str:
        """Следующая строка с переводом строки; пустая — конец ввода."""


class Console:
    """Ввод построчно в отдельном потоке — ожидание строки не блокирует цикл (R-34)."""

    def __init__(self, stdin: LineSource, out: TextIO) -> None:
        self._stdin = stdin
        self.out = out

    async def read_line(self) -> str | None:
        """Следующая строка или None в конце ввода."""
        line = await asyncio.to_thread(self._stdin.readline)
        return line or None


def main(argv: Sequence[str], env: Mapping[str, str], console: Console) -> int:
    """Код возврата: 0 — штатный выход, 1 — ошибка конфига, 2 — LLM недоступна (чат).

    Файлы логов и трасс открываются здесь, вне цикла событий, и живут до выхода.
    """
    args = _parse(argv)
    try:
        cfg = load_app_config(args.root, env)
        persona = load_persona(args.root / cfg.persona.file)
        with ExitStack() as files:
            log_file = files.enter_context(_open(args.root / cfg.logging.file))
            files.enter_context(logging_to(cfg.logging, log_file))
            traces = files.enter_context(_open(args.root / cfg.telemetry.traces_file))
            return asyncio.run(_run(args.mode, cfg, persona, console, traces))
    except ConfigError as exc:  # в т.ч. неизвестный `[llm].backend` — выясняется при сборке
        print(f"Ошибка конфигурации: {exc}", file=console.out)
        return EXIT_CONFIG


async def _run(
    mode: str, cfg: AppConfig, persona: Persona, console: Console, traces: TextIO
) -> int:
    bus = EventBus()
    core = Core(bus, Telemetry(bus))
    bus.subscribe(MetricRecorded, TraceWriter(traces))
    async with llm_backends().create(cfg.llm.backend, cfg.llm) as llm, asyncio.TaskGroup() as tg:
        metrics = tg.create_task(core.telemetry.run())
        service, prompts = build_conversation(cfg, persona, llm, core)
        if mode == SERVE_MODE:
            code = await _serve(cfg, service, _Warmup(llm, prompts.prefix, bus), console)
        else:
            code = await _chat(service, _Warmup(llm, prompts.prefix, bus), console, bus)
        metrics.cancel()
    return code


async def _chat(
    service: ConversationService, warmup: "_Warmup", console: Console, bus: EventBus
) -> int:
    if (problem := await warmup.run()) is not None:
        print(f"LLM недоступна: {problem}", file=console.out)
        return EXIT_UNAVAILABLE
    await TerminalChat(service, bus, console.read_line, console.out).run()
    return 0


async def _serve(
    cfg: AppConfig, service: ConversationService, warmup: "_Warmup", console: Console
) -> int:
    """Шлюз живёт, пока открыт stdin: Tauri-родитель умер — pipe закрыт — ядро выходит."""
    async with GatewayServer(service, warmup.bus, cfg.gateway) as server:
        print(f"Шлюз для UI: ws://{cfg.gateway.host}:{server.port}", file=console.out)
        if (problem := await warmup.run()) is not None:
            _log.warning("llm.unavailable_at_start", problem=problem)
        async with asyncio.TaskGroup() as tg:
            serving = tg.create_task(server.serve_forever())
            while await console.read_line() is not None:
                pass
            serving.cancel()
    return 0


class _Warmup:
    """Прогрев префикса промпта (T-06) со статусом LLM для UI: загружается → готова / сбой."""

    def __init__(self, llm: LLMPort, prefix: Sequence[Message], bus: EventBus) -> None:
        self._llm = llm
        self._prefix = prefix
        self.bus = bus

    async def run(self) -> str | None:
        """None — LLM готова; иначе — текст проблемы."""
        await self.bus.publish(BackendStatusChanged(Component.LLM, BackendState.LOADING))
        try:
            await self._llm.prefill(self._prefix)
        except LLMUnavailable as exc:
            await self.bus.publish(BackendStatusChanged(Component.LLM, BackendState.FAILED))
            return str(exc)
        await self.bus.publish(BackendStatusChanged(Component.LLM, BackendState.READY))
        _log.info("llm.ready")
        return None


def _open(path: Path) -> TextIO:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.open("a", encoding="utf-8")


def _parse(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="vtuber", description=__doc__)
    parser.add_argument("mode", nargs="?", choices=(CHAT_MODE, SERVE_MODE), default=CHAT_MODE)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="корень проекта (config/)")
    return parser.parse_args(argv)


def run() -> int:
    """Запуск из консоли: `python -m vtuber [chat|serve] [--root путь]`."""
    return main(sys.argv[1:], os.environ, Console(sys.stdin, sys.stdout))
