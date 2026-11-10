"""Чаты на ходу (Этап 21, ADR-0037): своя память и история у каждого чата, без перезапуска ядра.

Модели (LLM фона, e5) общие; на чат открываются база фактов, заметки, планировщик и запись чатов.
Память открывает и закрывает одна задача-владелец: `TaskGroup` внутри памяти должен войти и выйти
в одной задаче. Части памяти подписаны на шину чата, а не на общую: ретранслятор пересылает им ходы
только открытого чата, поэтому закрытый чат событий больше не получает.
"""

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import AsyncExitStack
from typing import NoReturn

from vtuber.application.memory import MemoryControls
from vtuber.bootstrap.config import AppConfig, MemoryConfig
from vtuber.bootstrap.container import Conversation, Core
from vtuber.bootstrap.memory import SharedMemory, chat_memory
from vtuber.domain import (
    MAIN_CHAT,
    CancelReason,
    TurnCancelled,
    TurnFinished,
    TurnRemembered,
    TurnStarted,
)
from vtuber.kernel import EventBus, get_logger

type MemoryFor = Callable[[str], MemoryConfig]
"""Чат → секция `[memory]` с его путями (`MemoryConfig.resolved`)."""
type OnOpen = Callable[[MemoryControls | None, Core], Awaitable[None]]
"""Чат открыт: переподключить панели UI к его памяти и показать его историю."""

_RELAYED = (TurnStarted, TurnFinished, TurnCancelled, TurnRemembered)
_log = get_logger(__name__)


def chat_profile(chat_id: str, base: str) -> str:
    """Профиль памяти чата: у основного — прежний (данные на старых путях), у других — свой."""
    return base if chat_id == MAIN_CHAT else f"chat-{chat_id}"


class ChatRelay:
    """Пересылает ходы с общей шины на шину открытого чата."""

    def __init__(self, bus: EventBus) -> None:
        self.chat_bus = EventBus()
        for event_type in _RELAYED:
            bus.subscribe(event_type, self._forward)

    def renew(self) -> EventBus:
        """Новая шина для следующего чата: подписчики прошлого отрезаны."""
        self.chat_bus = EventBus()
        return self.chat_bus

    async def _forward(self, event: object) -> None:
        await self.chat_bus.publish(event)


class ChatSwitcher:
    """Открытый чат и его смена; `run` — задача-владелец памяти, `switch` — просьба сменить."""

    def __init__(
        self,
        cfg: AppConfig,
        memory_for: MemoryFor,
        shared: SharedMemory | None,
        parts: tuple[Conversation, Core],
    ) -> None:
        self._cfg = cfg
        self._memory_for = memory_for
        self._shared = shared
        self._conversation, self._core = parts
        self._relay = ChatRelay(self._core.bus)
        self._requests: asyncio.Queue[tuple[str, asyncio.Future[None]]] = asyncio.Queue()
        self.on_open: OnOpen | None = None

    async def run(self, first: str) -> NoReturn:
        """Держит память открытого чата; новый запрос закрывает её и открывает следующую."""
        chat_id, done = first, None
        while True:
            async with AsyncExitStack() as stack:
                controls = await self._open(stack, chat_id)
                if self.on_open is not None:
                    await self.on_open(controls, Core(self._relay.chat_bus, self._core.telemetry))
                if done is not None:
                    done.set_result(None)
                chat_id, done = await self._requests.get()
                await self._conversation.service.cancel(CancelReason.USER_STOP)
            self._conversation.history.clear()

    async def switch(self, chat_id: str) -> None:
        """Сменить чат; возвращается, когда новый чат открыт и показан."""
        done: asyncio.Future[None] = asyncio.get_running_loop().create_future()
        await self._requests.put((chat_id, done))
        await done

    async def _open(self, stack: AsyncExitStack, chat_id: str) -> MemoryControls | None:
        bus = self._relay.renew()
        if self._shared is None:
            return None
        cfg = self._cfg.model_copy(update={"memory": self._memory_for(chat_id)})
        core = Core(bus, self._core.telemetry)
        controls = await stack.enter_async_context(
            chat_memory(cfg, self._shared, self._conversation, core)
        )
        _log.info("chat.opened", chat=chat_id)
        return controls
