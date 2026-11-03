"""Снимки менеджера ресурсов для панели UI: только пока панель открыта, раз в секунду (S-12.10)."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Final

from vtuber.application.scheduler import ResourceSnapshot
from vtuber.gateway.protocol import OutboundMessage
from vtuber.gateway.protocol_extras import ResourcesMessage

SNAPSHOT_PERIOD_S: Final = 1.0
"""График в секундах; чаще — лишние кадры Svelte рядом с аватаром (NFR-05)."""


class ResourcesFeed:
    """Закрытая панель ничего не считает: задачи нет, пока UI не попросит."""

    def __init__(
        self,
        snapshot: Callable[[], ResourceSnapshot],
        send: Callable[[OutboundMessage], Awaitable[None]],
        period_s: float = SNAPSHOT_PERIOD_S,
    ) -> None:
        self._snapshot = snapshot
        self._send = send
        self._period_s = period_s
        self._task: asyncio.Task[None] | None = None

    @property
    def running(self) -> bool:
        """Идёт ли рассылка снимков."""
        return self._task is not None

    def set_enabled(self, *, enabled: bool) -> None:
        """Панель открыли или закрыли; повторный вызов ничего не меняет."""
        if enabled and self._task is None:
            self._task = asyncio.create_task(self._run())
        elif not enabled and self._task is not None:
            self._task.cancel()
            self._task = None

    async def _run(self) -> None:
        while True:
            await self._send(ResourcesMessage.of(self._snapshot()))
            await asyncio.sleep(self._period_s)
