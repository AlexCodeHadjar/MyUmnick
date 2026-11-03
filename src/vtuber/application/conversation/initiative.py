"""Инициативные реплики (FR-23): персонаж сам заговаривает, только когда это никому не мешает."""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import NoReturn

from pydantic import Field

from vtuber.kernel import ConfigSection, get_logger

type Clock = Callable[[], float]
"""Монотонное время в секундах (`time.monotonic`)."""
type Sleep = Callable[[float], Awaitable[None]]

_log = get_logger(__name__)


class InitiativeConfig(ConfigSection):
    """Секция `[initiative]`: выключена по умолчанию, персонаж молчит, пока его не попросят."""

    enabled: bool
    idle_after_s: float = Field(gt=0)
    max_unanswered: int = Field(ge=1)
    when_hidden: bool
    poll_s: float = Field(gt=0)


@dataclass(frozen=True, slots=True)
class InitiativeActions:
    """`speak` возвращается, когда реплика прозвучала; `blocked` — занято: ход, речь, набор, фон."""

    speak: Callable[[], Awaitable[None]]
    stop: Callable[[], Awaitable[None]]
    blocked: Callable[[], bool]


class Initiative:
    """Считает тишину и говорит, когда её набралось; `user_input` обрывает реплику сразу.

    Занятость опрашивается, а не приходит событиями: простой редкий и долгий, опрос раз в секунду
    ничего не стоит, а тишина считается от конца речи, а не от конца хода (синтез быстрее речи).
    """

    def __init__(
        self,
        cfg: InitiativeConfig,
        actions: InitiativeActions,
        clock: Clock = time.monotonic,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._cfg = cfg
        self._actions = actions
        self._clock = clock
        self._sleep = sleep
        self._quiet_since = clock()
        self._unanswered = 0
        self._visible = True
        self._input = asyncio.Event()

    def user_input(self) -> None:
        """Ведущий что-то сделал: тишина и счётчик сначала, идущая реплика обрывается."""
        self._quiet_since = self._clock()
        self._unanswered = 0
        self._input.set()

    def set_visible(self, *, visible: bool) -> None:
        """Окно свернули или вернули: вернувшийся не услышит реплику в ту же секунду."""
        if visible and not self._visible:
            self._quiet_since = self._clock()
        self._visible = visible

    async def run(self) -> NoReturn:
        """Цикл на всё время работы; владелец — bootstrap."""
        while True:
            await self._sleep(self._cfg.poll_s)
            if self._actions.blocked():
                self._quiet_since = self._clock()
            elif self._is_due():
                await self._speak()

    def _is_due(self) -> bool:
        if self._unanswered >= self._cfg.max_unanswered:
            return False
        if not self._visible and not self._cfg.when_hidden:
            return False
        return self._clock() - self._quiet_since >= self._cfg.idle_after_s

    async def _speak(self) -> None:
        self._unanswered += 1
        self._input.clear()
        speaking = asyncio.create_task(self._say())
        interrupted = asyncio.create_task(self._input.wait())
        try:
            await asyncio.wait({speaking, interrupted}, return_when=asyncio.FIRST_COMPLETED)
            if not speaking.done():
                speaking.cancel()
                await asyncio.wait({speaking})
                await self._actions.stop()
        finally:
            speaking.cancel()
            interrupted.cancel()
        self._quiet_since = self._clock()

    async def _say(self) -> None:
        try:
            await self._actions.speak()
        except Exception as exc:  # noqa: BLE001 — R-42: реплику никто не просил, сбой не важнее работы
            _log.warning("initiative.failed", problem=repr(exc))
