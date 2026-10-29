"""Корень композиции: конфиг, персона, сборка графа объектов и точка входа."""

from vtuber.bootstrap.config import AppConfig, MemoryConfig, load_app_config
from vtuber.bootstrap.container import (
    Backends,
    Conversation,
    Core,
    build_conversation,
    llm_backends,
    tts_backends,
)
from vtuber.bootstrap.main import Console, main, run
from vtuber.bootstrap.persona import PersonaConfig, load_persona

__all__ = [
    "AppConfig",
    "Backends",
    "Console",
    "Conversation",
    "Core",
    "MemoryConfig",
    "PersonaConfig",
    "build_conversation",
    "llm_backends",
    "load_app_config",
    "load_persona",
    "main",
    "run",
    "tts_backends",
]
