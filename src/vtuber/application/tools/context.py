"""Сбор справки от инструментов плагинов: чужой код, поэтому с жёстким сроком в горячем пути."""

import asyncio
from collections.abc import Sequence

from vtuber.application.memory import TurnHints
from vtuber.kernel import ContextTool, get_logger

_log = get_logger(__name__)


class ToolContext:
    """Опрашивает инструменты параллельно; не успели или упали — ход идёт без них (приоритет 1)."""

    def __init__(self, tools: Sequence[ContextTool], timeout_s: float) -> None:
        self._tools = tuple(tools)
        self._timeout_s = timeout_s

    async def hints(self, text: str) -> TurnHints:
        """Справка для реплики `text`."""
        answers = await asyncio.gather(*(self._ask(tool, text) for tool in self._tools))
        return TurnHints(context=tuple(line for line in answers if line))

    async def _ask(self, tool: ContextTool, text: str) -> str | None:
        limit = self._timeout_s if tool.timeout_s is None else tool.timeout_s
        try:
            async with asyncio.timeout(limit):
                return await tool.provider(text)
        except TimeoutError:
            _log.warning("tools.too_slow")
        except Exception as exc:  # noqa: BLE001 — R-42: инструмент — чужой код, ход важнее
            _log.warning("tools.failed", problem=repr(exc))
        return None
