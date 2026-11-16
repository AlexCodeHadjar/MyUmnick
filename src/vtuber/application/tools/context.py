"""Сбор справки от инструментов плагинов: чужой код, поэтому с жёстким сроком в горячем пути."""

import asyncio
import time
from collections.abc import Sequence

from vtuber.application.memory import TurnHints
from vtuber.application.skills import SkillGate
from vtuber.kernel import ContextTool, get_logger

_log = get_logger(__name__)


class ToolContext:
    """Опрашивает инструменты параллельно; не успели или упали — ход идёт без них (приоритет 1).

    `tools` читается на каждой реплике: плагин, включённый в панели «Навыки», дописывает в него
    свои инструменты на ходу. Выключенный навык не опрашивается вовсе (ADR-0043).
    """

    def __init__(
        self, tools: Sequence[ContextTool], timeout_s: float, skills: SkillGate | None = None
    ) -> None:
        self._tools = tools
        self._timeout_s = timeout_s
        self._skills = skills

    async def hints(self, text: str) -> TurnHints:
        """Справка для реплики `text`."""
        active = [tool for tool in self._tools if self._enabled(tool)]
        answers = await asyncio.gather(*(self._ask(tool, text) for tool in active))
        return TurnHints(context=tuple(line for line in answers if line))

    def _enabled(self, tool: ContextTool) -> bool:
        return self._skills is None or self._skills.enabled(tool.skill)

    async def _ask(self, tool: ContextTool, text: str) -> str | None:
        limit = self._timeout_s if tool.timeout_s is None else tool.timeout_s
        started = time.perf_counter()
        try:
            async with asyncio.timeout(limit):
                answer = await tool.provider(text)
        except TimeoutError:
            _log.warning("tools.too_slow", skill=tool.skill)
            self._record(tool, None)
        except Exception as exc:  # noqa: BLE001 — R-42: инструмент — чужой код, ход важнее
            _log.warning("tools.failed", problem=repr(exc), skill=tool.skill)
        else:
            if answer:
                self._record(tool, (time.perf_counter() - started) * 1000)
            return answer
        return None

    def _record(self, tool: ContextTool, ms: float | None) -> None:
        if self._skills is not None:
            self._skills.record(tool.skill, ms)
