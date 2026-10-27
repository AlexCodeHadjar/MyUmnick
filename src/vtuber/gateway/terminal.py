"""Терминальный чат (веха M1): реплики из строк ввода, ответ — потоком в консоль, TTFT."""

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Final, TextIO

from vtuber.application.conversation import ConversationService
from vtuber.domain import CancelReason, Emotion, TurnCancelled, TurnFinished, TurnId
from vtuber.kernel import EventBus

EXIT_COMMAND: Final = "/exit"
STOP_COMMAND: Final = "/stop"
NS_PER_MS: Final = 1_000_000
HELP: Final = f"Пишите реплику и Enter. {STOP_COMMAND} — прервать ответ, {EXIT_COMMAND} — выход."

type LineReader = Callable[[], Awaitable[str | None]]


@dataclass(slots=True)
class TerminalSink:
    """ReplySink для консоли: печатает ответ по мере генерации и помнит время первой порции.

    Запись в консоль синхронная, но это несколько байт на порцию в инструменте разработчика.
    """

    out: TextIO
    started_ns: int
    clock: Callable[[], int] = time.perf_counter_ns
    first_output_ns: int | None = field(default=None)

    async def text(self, delta: str) -> None:
        """Печатает порцию ответа."""
        self._mark()
        self._write(delta)

    async def emotion(self, emotion: Emotion) -> None:
        """Показывает смену эмоции как `[happy]`."""
        self._mark()
        self._write(f"[{emotion.value}] ")

    async def done(self) -> None:
        """Завершает строку ответа."""
        self._write("\n")

    def _mark(self) -> None:
        if self.first_output_ns is None:
            self.first_output_ns = self.clock()

    def _write(self, text: str) -> None:
        self.out.write(text)
        self.out.flush()


class TerminalChat:
    """Цикл чата: строка → ход; новая строка во время ответа прерывает его (T-14).

    После каждого ответа печатает TTFT — время до первой показанной порции.
    """

    def __init__(
        self, service: ConversationService, bus: EventBus, read_line: LineReader, out: TextIO
    ) -> None:
        self._service = service
        self._read_line = read_line
        self._out = out
        self._sinks: dict[TurnId, TerminalSink] = {}
        bus.subscribe(TurnFinished, self._on_finished)
        bus.subscribe(TurnCancelled, self._on_cancelled)

    async def run(self) -> None:
        """Читает строки до `/exit` или конца ввода; в конце дожидается текущего ответа."""
        self._print(HELP)
        while (line := await self._read_line()) is not None:
            command = line.strip()
            if command == EXIT_COMMAND:
                await self._service.cancel(CancelReason.USER_STOP)
                return
            if command == STOP_COMMAND:
                await self._service.cancel(CancelReason.USER_STOP)
            elif command:
                await self._send(command)
        await self._service.wait_idle()

    async def _send(self, text: str) -> None:
        sink = TerminalSink(self._out, time.perf_counter_ns())
        self._out.write("Мика: ")
        turn_id = await self._service.handle(text, sink)
        self._sinks[turn_id] = sink

    async def _on_finished(self, event: TurnFinished) -> None:
        sink = self._sinks.pop(event.turn_id, None)
        if sink is not None and sink.first_output_ns is not None:
            ttft_ms = (sink.first_output_ns - sink.started_ns) / NS_PER_MS
            self._print(f"  · TTFT {ttft_ms:.0f} мс")

    async def _on_cancelled(self, event: TurnCancelled) -> None:
        self._sinks.pop(event.turn_id, None)
        note = event.message or f"прервано ({event.reason.value})"
        self._print(f"\n  · {note}")

    def _print(self, text: str) -> None:
        self._out.write(f"{text}\n")
        self._out.flush()
