"""Сбор справки от инструментов плагинов: чужой код, поэтому с жёстким сроком в горячем пути."""

import asyncio
from collections.abc import Sequence

from vtuber.application.memory import TurnHints
from vtuber.kernel import ContextProvider, get_logger

_log = get_logger(__name__)


class ToolContext:
    """Опрашивает инструменты параллельно; не успели или упали — ход идёт без них (приоритет 1)."""

    def __init__(self, providers: Sequence[ContextProvider], timeout_s: float) -> None:
        self._providers = tuple(providers)
        self._timeout_s = timeout_s

    async def hints(self, text: str) -> TurnHints:
        """Справка для реплики `text`."""
        tasks = [asyncio.ensure_future(provider(text)) for provider in self._providers]
        done, late = await asyncio.wait(tasks, timeout=self._timeout_s)
        for task in late:
            task.cancel()
            _log.warning("tools.too_slow")
        return TurnHints(
            context=tuple(line for task in tasks if task in done and (line := _result(task)))
        )


def _result(task: asyncio.Future[str | None]) -> str | None:
    if task.cancelled():
        return None
    if (error := task.exception()) is not None:
        _log.warning("tools.failed", problem=repr(error))
        return None
    return task.result()
