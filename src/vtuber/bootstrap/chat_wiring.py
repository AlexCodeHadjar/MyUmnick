"""Память приложения с чатами (Этап 21, ADR-0037): в `serve` — каталог и смена чата."""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from vtuber.adapters.chats import JsonChatCatalog
from vtuber.application.chats import ChatDirectory
from vtuber.application.memory import MemoryControls
from vtuber.bootstrap.chats import ChatSwitcher, chat_profile
from vtuber.bootstrap.config import AppConfig, MemoryConfig
from vtuber.bootstrap.container import Conversation, Core
from vtuber.bootstrap.memory import SharedMemory, background_memory, shared_memory
from vtuber.domain import MAIN_CHAT

CATALOG_FILE = "chats.json"


@dataclass(slots=True)
class MemoryAccess:
    """Память открытого чата и всё для смены; поля меняются при переключении.

    `on_switched` ставит шлюз: переподключить панели к памяти нового чата и показать его историю.
    """

    controls: MemoryControls | None
    chat_core: Core
    switcher: ChatSwitcher | None = None
    directory: ChatDirectory | None = None
    on_switched: Callable[[], Awaitable[None]] | None = None

    def is_working(self) -> bool:
        """Идёт ли фоновая работа памяти открытого чата."""
        return self.controls is not None and self.controls.is_working()


@asynccontextmanager
async def app_memory(
    cfg: AppConfig, conversation: Conversation, core: Core, *, chats: bool
) -> AsyncIterator[MemoryAccess]:
    """Память на время работы; `chats=False` — один разговор, как до Этапа 21 (терминал)."""
    if not chats:
        async with background_memory(cfg, conversation, core) as controls:
            yield MemoryAccess(controls, core)
        return
    async with shared_memory(cfg) as shared, asyncio.TaskGroup() as tg:
        access, switcher = await _chats(cfg, conversation, core, shared)
        opened = asyncio.Event()
        switcher.on_open = _opener(access, opened)
        owner = tg.create_task(switcher.run(_active(access)))
        await opened.wait()
        try:
            yield access
        finally:
            owner.cancel()


async def _chats(
    cfg: AppConfig, conversation: Conversation, core: Core, shared: SharedMemory | None
) -> tuple[MemoryAccess, ChatSwitcher]:
    """Каталог из файла, подписка на ходы (названия чатов) и переключатель памяти."""
    memory_for = _memory_for(cfg.memory)
    catalog = JsonChatCatalog(
        cfg.memory.store_path.parent / CATALOG_FILE,
        lambda chat_id: _locate(memory_for(chat_id)),
    )
    directory = ChatDirectory(catalog, await catalog.load())
    directory.follow(core.bus)
    switcher = ChatSwitcher(cfg, memory_for, shared, (conversation, core))
    return MemoryAccess(None, core, switcher, directory), switcher


def _opener(
    access: MemoryAccess, opened: asyncio.Event
) -> Callable[[MemoryControls | None, Core], Awaitable[None]]:
    async def on_open(controls: MemoryControls | None, chat_core: Core) -> None:
        access.controls, access.chat_core = controls, chat_core
        if access.on_switched is not None:
            await access.on_switched()
        opened.set()

    return on_open


def _active(access: MemoryAccess) -> str:
    return MAIN_CHAT if access.directory is None else access.directory.chats.active


def _memory_for(memory: MemoryConfig) -> Callable[[str], MemoryConfig]:
    base = memory.profile

    def for_chat(chat_id: str) -> MemoryConfig:
        return memory.with_profile(chat_profile(chat_id, base))

    return for_chat


def _locate(memory: MemoryConfig) -> tuple[Path, Path]:
    return memory.store_path, memory.vault_path
