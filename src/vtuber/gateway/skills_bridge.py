"""Панель «Навыки» ↔ реестр (Этап 23, ADR-0043)."""

import asyncio
from collections.abc import Awaitable, Callable

from vtuber.application.skills import SkillRegistry
from vtuber.domain import ConfigError, SkillInfo
from vtuber.gateway.protocol import OutboundMessage
from vtuber.gateway.protocol_skills import SkillsAction, SkillsState

type Discover = Callable[[], Awaitable[tuple[SkillInfo, ...]]]
"""Установленные, но не запущенные плагины."""


class SkillsBridge:
    """Действия по одному: включение плагина на ходу не должно пересечься со вторым."""

    def __init__(
        self,
        registry: SkillRegistry,
        discover: Discover,
        send: Callable[[OutboundMessage], Awaitable[None]],
    ) -> None:
        self._registry = registry
        self._discover = discover
        self._send = send
        self._lock = asyncio.Lock()

    async def send_state(self, problem: str | None = None) -> None:
        """Список целиком."""
        await self._send(SkillsState.of(self._registry.states(), problem))

    async def handle(self, message: SkillsAction) -> None:
        """Выполняет действие; ошибка показывается в панели, соединение живёт."""
        async with self._lock:
            data = message.data
            if data.action == "list":
                # Пакеты ищутся только при открытии панели: обычный запуск их не ищет.
                self._registry.offer(await self._discover())
                await self.send_state()
                return
            if data.id is None or data.enabled is None:
                await self.send_state("В действии с навыком не хватает поля")
                return
            try:
                await self._registry.set(data.id, enabled=data.enabled)
            except (ValueError, ConfigError) as exc:
                await self.send_state(str(exc))
                return
            await self.send_state()
