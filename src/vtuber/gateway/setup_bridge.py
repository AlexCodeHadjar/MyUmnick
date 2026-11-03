"""Мастер первого запуска ↔ UI (S-13.2): состояние при подключении, установка, ход загрузки."""

import time
from collections.abc import Awaitable, Callable
from typing import Final

from vtuber.application.setup import InstallProgress, SetupChoice, SetupWizard
from vtuber.domain import SetupFailed
from vtuber.gateway.protocol import OutboundMessage
from vtuber.gateway.protocol_extras import (
    SetupCancel,
    SetupFinished,
    SetupInstall,
    SetupProgress,
    SetupStateMessage,
)

PROGRESS_PERIOD_S: Final = 0.25
"""Индикатору хватает четырёх обновлений в секунду; поток загрузки — десятки порций."""


class SetupBridge:
    """Переводит сообщения UI в вызовы мастера; ход установки шлёт реже, чем приходят данные."""

    def __init__(
        self, wizard: SetupWizard, send: Callable[[OutboundMessage], Awaitable[None]]
    ) -> None:
        self._wizard = wizard
        self._send = send
        self._last_progress = 0.0

    async def send_state(self) -> None:
        """Состояние для UI: мастер показывается, если оно говорит, что нужен."""
        state = await self._wizard.state()
        await self._send(SetupStateMessage.of(state, self._wizard.catalog))

    async def handle(self, message: SetupInstall | SetupCancel) -> None:
        """Согласие на загрузку или её отмена; без `setup.install` ничего не скачивается."""
        if isinstance(message, SetupCancel):
            self._wizard.cancel()
            return
        choice = SetupChoice(tuple(message.data.item_ids), message.data.voice)
        try:
            self._wizard.start(choice, self._progress, self._finished)
        except SetupFailed as exc:
            await self._send(SetupFinished.of(str(exc)))

    async def _progress(self, progress: InstallProgress) -> None:
        now = time.monotonic()
        last = progress.done == progress.total
        if last or now - self._last_progress >= PROGRESS_PERIOD_S:
            self._last_progress = now
            await self._send(SetupProgress.of(progress))

    async def _finished(self, problem: str | None) -> None:
        await self._send(SetupFinished.of(problem))
