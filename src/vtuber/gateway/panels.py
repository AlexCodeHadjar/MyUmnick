"""Панели UI вне хода диалога: мастер, ресурсы, память, ветки; у каждой свой мост."""

from dataclasses import dataclass

from vtuber.gateway.branch_bridge import BranchBridge
from vtuber.gateway.memory_bridge import MemoryBridge
from vtuber.gateway.privacy_bridge import PrivacyBridge
from vtuber.gateway.protocol_branches import BranchCheckpoint, BranchGo
from vtuber.gateway.protocol_extras import ResourcesWatch, SetupCancel, SetupInstall
from vtuber.gateway.protocol_memory import (
    MemoryErase,
    MemoryFactDelete,
    MemoryFactSave,
    MemoryList,
    PrivacySet,
)
from vtuber.gateway.resources_feed import ResourcesFeed
from vtuber.gateway.setup_bridge import SetupBridge

type _SetupMessage = SetupInstall | SetupCancel
type _PrivacyMessage = PrivacySet | MemoryErase
type _MemoryMessage = MemoryList | MemoryFactSave | MemoryFactDelete
type _BranchMessage = BranchGo | BranchCheckpoint
type PanelMessage = (
    ResourcesWatch | _SetupMessage | _PrivacyMessage | _MemoryMessage | _BranchMessage
)


@dataclass(slots=True)
class Panels:
    """Панель не подключена — её сообщения просто не нужны."""

    resources: ResourcesFeed | None = None
    setup: SetupBridge | None = None
    privacy: PrivacyBridge | None = None
    memory: MemoryBridge | None = None
    branches: BranchBridge | None = None

    async def greet(self) -> None:
        """Что новый клиент должен узнать сразу: окно могло перезапуститься посреди работы."""
        if self.setup is not None:
            await self.setup.send_state()
        if self.privacy is not None:
            await self.privacy.send_state()
        if self.branches is not None:
            await self.branches.send_state()

    def client_gone(self) -> None:
        """Некому показывать снимки ресурсов."""
        if self.resources is not None:
            self.resources.set_enabled(enabled=False)

    async def handle(self, message: PanelMessage) -> None:
        """Передаёт сообщение мосту его панели."""
        if isinstance(message, ResourcesWatch):
            if self.resources is not None:
                self.resources.set_enabled(enabled=message.data.enabled)
        elif isinstance(message, SetupInstall | SetupCancel):
            if self.setup is not None:
                await self.setup.handle(message)
        else:
            await self._handle_dialogue(message)

    async def _handle_dialogue(
        self, message: _PrivacyMessage | _MemoryMessage | _BranchMessage
    ) -> None:
        if isinstance(message, PrivacySet | MemoryErase):
            if self.privacy is not None:
                await self.privacy.handle(message)
        elif isinstance(message, BranchGo | BranchCheckpoint):
            if self.branches is not None:
                await self.branches.handle(message)
        elif self.memory is not None:
            await self.memory.handle(message)
