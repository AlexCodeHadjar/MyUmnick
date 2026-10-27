"""Точка входа: терминальный чат с витюбером (`uv run python -m vtuber`), веха M1."""

import argparse
import asyncio
import os
import sys
from collections.abc import Mapping, Sequence
from contextlib import ExitStack
from pathlib import Path
from typing import Final, TextIO

from vtuber.bootstrap.config import AppConfig, load_app_config
from vtuber.bootstrap.container import Core, build_conversation, llm_backends
from vtuber.bootstrap.persona import load_persona
from vtuber.domain import ConfigError, LLMUnavailable, MetricRecorded, Persona
from vtuber.gateway import TerminalChat
from vtuber.kernel import EventBus, Telemetry, TraceWriter, configure_logging, get_logger

EXIT_CONFIG: Final = 1
EXIT_UNAVAILABLE: Final = 2

_log = get_logger(__name__)


class Console:
    """Ввод построчно в отдельном потоке — ожидание строки не блокирует цикл (R-34)."""

    def __init__(self, stdin: TextIO, out: TextIO) -> None:
        self._stdin = stdin
        self.out = out

    async def read_line(self) -> str | None:
        """Следующая строка или None в конце ввода."""
        line = await asyncio.to_thread(self._stdin.readline)
        return line or None


def main(argv: Sequence[str], env: Mapping[str, str], console: Console) -> int:
    """Код возврата: 0 — чат завершён, 1 — ошибка конфига, 2 — LLM-сервер недоступен.

    Файлы логов и трасс открываются здесь, вне цикла событий, и живут до выхода.
    """
    root = _parse(argv).root
    try:
        cfg = load_app_config(root, env)
        persona = load_persona(root / cfg.persona.file)
        with ExitStack() as files:
            configure_logging(cfg.logging, files.enter_context(_open(root / cfg.logging.file)))
            traces = files.enter_context(_open(root / cfg.telemetry.traces_file))
            return asyncio.run(_chat(cfg, persona, console, traces))
    except ConfigError as exc:  # в т.ч. неизвестный `[llm].backend` — выясняется при сборке
        print(f"Ошибка конфигурации: {exc}", file=console.out)
        return EXIT_CONFIG


async def _chat(cfg: AppConfig, persona: Persona, console: Console, traces: TextIO) -> int:
    bus = EventBus()
    core = Core(bus, Telemetry(bus))
    bus.subscribe(MetricRecorded, TraceWriter(traces))
    async with llm_backends().create(cfg.llm.backend, cfg.llm) as llm, asyncio.TaskGroup() as tg:
        metrics = tg.create_task(core.telemetry.run())
        service, prompts = build_conversation(cfg, persona, llm, core)
        try:
            await llm.prefill(prompts.prefix)  # T-06: первый ответ не платит за холодный старт
        except LLMUnavailable as exc:
            print(f"LLM недоступна: {exc}", file=console.out)
            metrics.cancel()
            return EXIT_UNAVAILABLE
        _log.info("chat.ready", backend=cfg.llm.backend)
        await TerminalChat(service, bus, console.read_line, console.out).run()
        metrics.cancel()
    return 0


def _open(path: Path) -> TextIO:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.open("a", encoding="utf-8")


def _parse(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="vtuber", description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="корень проекта (config/)")
    return parser.parse_args(argv)


def run() -> int:
    """Запуск из консоли: `python -m vtuber [--root путь]`."""
    return main(sys.argv[1:], os.environ, Console(sys.stdin, sys.stdout))
