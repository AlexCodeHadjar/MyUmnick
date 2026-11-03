"""Наблюдатель за компонентами (S-17.1): сбой или зависание — перезапуск с паузой и пределом.

Работает своей задачей рядом с ходом, а не внутри него. Ход при падении компонента заканчивается
понятной ошибкой сам (порты бросают `*Unavailable`), здесь — только возврат компонента в строй.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from pydantic import Field

from vtuber.domain import BackendNotice, BackendState, BackendStatusChanged, Component, VtuberError
from vtuber.kernel import ConfigSection, EventBus, get_logger

_log = get_logger(__name__)

_TITLES = {
    Component.LLM: "Языковая модель",
    Component.TTS: "Голос",
    Component.STT: "Распознавание речи",
}


class SupervisorConfig(ConfigSection):
    """Секция `[supervisor]`: как часто проверять и сколько раз пытаться поднять компонент."""

    enabled: bool
    check_s: float = Field(gt=0)
    health_timeout_s: float = Field(gt=0)
    failures_to_restart: int = Field(ge=1)
    backoff_s: float = Field(gt=0)
    backoff_max_s: float = Field(gt=0)
    max_attempts: int = Field(ge=1)
    stable_s: float = Field(gt=0)
    voice_timeout_s: float = Field(gt=0)
    stt_timeout_s: float = Field(gt=0)


@dataclass(slots=True)
class _Track:
    """Что наблюдатель помнит об одном компоненте."""

    failures: int = 0
    attempts: int = 0
    gave_up: bool = False
    recovered_at: float = 0.0


class Supervised(Protocol):
    """Компонент под наблюдением."""

    @property
    def component(self) -> Component:
        """Что показывать в статусе."""
        ...

    async def healthy(self) -> bool:
        """Работает ли он сейчас; не дольше `health_timeout_s`, иначе считается зависшим."""
        ...

    async def restart(self) -> None:
        """Поднять заново.

        Raises:
            VtuberError: не поднялся.

        """
        ...


class Supervisor:
    """Следит за каждым компонентом отдельно: падение одного не задерживает проверку другого."""

    def __init__(
        self,
        items: Sequence[Supervised],
        cfg: SupervisorConfig,
        bus: EventBus,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._items = tuple(items)
        self._cfg = cfg
        self._bus = bus
        self._sleep = sleep

    async def run(self) -> None:
        """Следит, пока задачу не отменят."""
        async with asyncio.TaskGroup() as tg:
            for item in self._items:
                tg.create_task(self._watch(item))

    async def _watch(self, item: Supervised) -> None:
        track = _Track()
        while True:
            await self._sleep(self._cfg.check_s)
            if await self._is_healthy(item):
                await self._on_healthy(item, track)
            else:
                await self._on_unhealthy(item, track)

    async def _on_healthy(self, item: Supervised, track: _Track) -> None:
        track.failures = 0
        if track.gave_up:
            # Вернулся сам: например, пользователь поправил файл модели.
            track.gave_up = False
            track.attempts = 0
            await self._report(item, BackendState.READY, "снова работает")
        if track.attempts and time.monotonic() - track.recovered_at >= self._cfg.stable_s:
            track.attempts = 0  # проработал долго: следующий сбой — новая история, а не цикл

    async def _on_unhealthy(self, item: Supervised, track: _Track) -> None:
        track.failures += 1
        if track.gave_up or track.failures < self._cfg.failures_to_restart:
            return
        track.attempts, track.gave_up = await self._recover(item, track.attempts)
        track.recovered_at = time.monotonic()
        track.failures = 0

    async def _is_healthy(self, item: Supervised) -> bool:
        try:
            async with asyncio.timeout(self._cfg.health_timeout_s):
                return await item.healthy()
        except TimeoutError:
            _log.warning("supervisor.health_timeout", component=item.component.value)
            return False

    async def _recover(self, item: Supervised, attempts: int) -> tuple[int, bool]:
        """Возвращает новое число попыток и признак «попытки кончились»."""
        while attempts < self._cfg.max_attempts:
            attempts += 1
            total = self._cfg.max_attempts
            await self._report(
                item, BackendState.LOADING, f"перезапускается, попытка {attempts} из {total}"
            )
            await self._sleep(self._pause(attempts))
            if await self._restarted(item):
                await self._report(item, BackendState.READY, "снова работает")
                return attempts, False
        await self._report(item, BackendState.FAILED, "не запускается, нужен перезапуск приложения")
        return attempts, True

    def _pause(self, attempt: int) -> float:
        return min(self._cfg.backoff_s * 2.0 ** (attempt - 1), self._cfg.backoff_max_s)

    async def _restarted(self, item: Supervised) -> bool:
        try:
            await item.restart()
        except VtuberError as exc:
            _log.warning(
                "supervisor.restart_failed", component=item.component.value, problem=str(exc)
            )
            return False
        except Exception:  # noqa: BLE001 — R-42: наблюдатель не должен умереть от сбоя компонента
            _log.exception("supervisor.restart_crashed", component=item.component.value)
            return False
        return True

    async def _report(self, item: Supervised, state: BackendState, what: str) -> None:
        _log.info("supervisor.state", component=item.component.value, state=state.value)
        await self._bus.publish(BackendStatusChanged(item.component, state))
        title = _TITLES[item.component]
        await self._bus.publish(BackendNotice(item.component, f"{title}: {what}"))
