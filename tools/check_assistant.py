"""Настоящий плагин помощника на настоящих серверах (S-12.6): одна задача от просьбы до чата.

Запуск: `uv run python -m tools.check_assistant [--main-url …] [--code-url …]`. Плагин должен быть
на пути (`PYTHONPATH=plugins/code_assistant/src`). Проверяет то, чего не видно на заглушке: перевод
основной моделью, код в чате и то, что в речь код не попал.
"""

import argparse
import asyncio
import sys
import time
from collections.abc import Sequence
from contextlib import aclosing
from dataclasses import dataclass, field
from typing import Final, TextIO

from vtuber.domain import TextShown
from vtuber.kernel import EventBus, PluginContext
from vtuber_code_assistant import CodeAssistantPlugin

TASK: Final = "Напиши функцию на питоне, которая проверяет, простое ли число."
EXIT_FAILED: Final = 1
RESULT_TIMEOUT_S: Final = 600.0
CODE_MARK: Final = "def "


@dataclass(slots=True)
class Outcome:
    """Что вышло: код в чате, фраза для голоса, время."""

    shown: list[str] = field(default_factory=list)
    spoken: str = ""
    seconds: float = 0.0

    @property
    def problem(self) -> str:
        """Пустая строка — всё верно."""
        if not self.shown:
            return f"в чате ничего нет; помощник сказал: {self.spoken}"
        if CODE_MARK not in self.shown[0]:
            return "в чате нет кода"
        return "код попал в речь" if CODE_MARK in self.spoken else ""


async def run_task(main_url: str, code_url: str, task: str = TASK) -> Outcome:
    """Как в приложении: `context` на реплику, результат — из источника плагина."""
    bus = EventBus()
    outcome = Outcome()

    async def on_text(event: TextShown) -> None:
        outcome.shown.append(event.text)

    bus.subscribe(TextShown, on_text)
    settings = {"main_url": main_url, "code_url": code_url, "timeout_s": RESULT_TIMEOUT_S}
    plugin = CodeAssistantPlugin()
    await plugin.setup(PluginContext("code_assistant", bus, settings))
    started = time.perf_counter()
    try:
        await plugin.context(task)
        async with aclosing(plugin.results()) as lines:
            message = await asyncio.wait_for(anext(lines), RESULT_TIMEOUT_S)
    finally:
        await plugin.shutdown()
    outcome.spoken = message.text
    outcome.seconds = time.perf_counter() - started
    return outcome


def main(argv: Sequence[str], out: TextIO) -> int:
    """Код возврата: 0 — верно, 1 — нет."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-url", default="http://127.0.0.1:8080")
    parser.add_argument("--code-url", default="http://127.0.0.1:8081")
    args = parser.parse_args(argv)
    outcome = asyncio.run(run_task(args.main_url, args.code_url))
    print(f"Время: {outcome.seconds:.1f} с\nРечь: {outcome.spoken}", file=out)
    print("Чат:", *outcome.shown, sep="\n", file=out)
    if outcome.problem:
        print(f"ПРОБЛЕМА: {outcome.problem}", file=out)
        return EXIT_FAILED
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:], sys.stdout))
