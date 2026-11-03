"""Подключение панелей к шлюзу: мастер первого запуска и управление памятью."""

from vtuber.adapters.gpu import NvidiaSmiProbe
from vtuber.application.conversation import ConversationService
from vtuber.application.memory import MemoryControls
from vtuber.bootstrap.config import AppConfig
from vtuber.bootstrap.setup import build_wizard
from vtuber.gateway import GatewayServer, MemoryBridge, PrivacyBridge, SetupBridge


def connect_memory(
    memory: MemoryControls | None, server: GatewayServer, service: ConversationService
) -> None:
    """Приватный режим работает и без памяти; редактор и очистка честно скажут, что её нет."""
    eraser = None if memory is None else memory.eraser
    editor = None if memory is None else memory.editor
    server.use_memory(
        PrivacyBridge(service, eraser, server.send), MemoryBridge(editor, server.send)
    )


def connect_setup(cfg: AppConfig, server: GatewayServer) -> None:
    """Мастер есть только в поставке: при разработке модели кладут сами."""
    if cfg.setup.enabled:
        wizard = build_wizard(cfg.setup, NvidiaSmiProbe(cfg.gpu_probe))
        server.use_setup(SetupBridge(wizard, server.send))
