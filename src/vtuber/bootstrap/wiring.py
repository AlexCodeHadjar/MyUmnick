"""Подключение панелей к шлюзу: мастер первого запуска и управление памятью."""

from dataclasses import dataclass

from vtuber.adapters.gpu import NvidiaSmiProbe
from vtuber.application.conversation import (
    ConversationService,
    DialogueTree,
    Initiative,
    InitiativeActions,
)
from vtuber.application.memory import MemoryControls, ShortTermMemory
from vtuber.application.scheduler import ResourceManager
from vtuber.bootstrap.config import AppConfig
from vtuber.bootstrap.container import Core
from vtuber.bootstrap.plugins import PluginServices
from vtuber.bootstrap.setup import build_wizard
from vtuber.domain import Persona
from vtuber.gateway import (
    BranchBridge,
    ExternalTurns,
    GatewayServer,
    MemoryBridge,
    PrivacyBridge,
    ResourcesFeed,
    SetupBridge,
)


@dataclass(frozen=True, slots=True)
class AppParts:
    """Что шлюзу нужно от приложения, кроме сервиса хода."""

    cfg: AppConfig
    core: Core
    plugins: PluginServices
    resources: ResourceManager
    memory: MemoryControls | None
    history: ShortTermMemory
    persona: Persona


def connect_memory(
    memory: MemoryControls | None, server: GatewayServer, service: ConversationService
) -> None:
    """Приватный режим работает и без памяти; редактор и очистка честно скажут, что её нет."""
    eraser = None if memory is None else memory.eraser
    editor = None if memory is None else memory.editor
    server.panels.privacy = PrivacyBridge(service, eraser, server.send)
    server.panels.memory = MemoryBridge(editor, server.send)


def connect_branches(
    history: ShortTermMemory, core: Core, server: GatewayServer, service: ConversationService
) -> None:
    """Дерево начинается с восстановленного разговора: его ветки тоже можно продолжить."""
    tree = DialogueTree()
    tree.seed(history.turns)
    tree.follow(core.bus)
    server.panels.branches = BranchBridge(service, tree, server.send)


def connect_panels(app: AppParts, server: GatewayServer, service: ConversationService) -> None:
    """Всё, что UI может сделать помимо реплики."""
    server.use_commands(app.plugins.commands)
    server.panels.resources = ResourcesFeed(app.resources.snapshot, server.send)
    connect_setup(app.cfg, server)
    connect_memory(app.memory, server, service)
    connect_branches(app.history, app.core, server, service)


def connect_initiative(
    app: AppParts, server: GatewayServer, service: ConversationService, external: ExternalTurns
) -> Initiative | None:
    """Персонаж сам заговаривает, только если это включили (S-15.1); фон памяти не прерывается."""
    if not app.cfg.initiative.enabled:
        return None
    memory = app.memory

    async def speak() -> None:
        await external.initiate(app.persona.initiative)

    def blocked() -> bool:
        working = memory is not None and memory.is_working()
        return service.engaged or working or not server.has_client

    actions = InitiativeActions(speak, external.stop_initiative, blocked)
    initiative = Initiative(app.cfg.initiative, actions)
    service.observe_input(initiative.user_input)
    server.panels.window = lambda visible: initiative.set_visible(visible=visible)
    return initiative


def connect_setup(cfg: AppConfig, server: GatewayServer) -> None:
    """Мастер есть только в поставке: при разработке модели кладут сами."""
    if cfg.setup.enabled:
        wizard = build_wizard(cfg.setup, NvidiaSmiProbe(cfg.gpu_probe))
        server.panels.setup = SetupBridge(wizard, server.send)
