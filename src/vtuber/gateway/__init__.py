"""Шлюз: интерфейсы к ядру — терминальный чат (M1), далее WebSocket-сервер для UI (Этап 4)."""

from vtuber.gateway.terminal import EXIT_COMMAND, STOP_COMMAND, TerminalChat, TerminalSink

__all__ = ["EXIT_COMMAND", "STOP_COMMAND", "TerminalChat", "TerminalSink"]
