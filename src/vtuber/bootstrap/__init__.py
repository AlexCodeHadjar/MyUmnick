"""Корень композиции: конфиг, персона, сборка графа объектов и точка входа."""

from vtuber.bootstrap.config import AppConfig, load_app_config
from vtuber.bootstrap.container import Core, build_conversation, llm_backends
from vtuber.bootstrap.main import Console, main, run
from vtuber.bootstrap.persona import PersonaConfig, load_persona

__all__ = [
    "AppConfig",
    "Console",
    "Core",
    "PersonaConfig",
    "build_conversation",
    "llm_backends",
    "load_app_config",
    "load_persona",
    "main",
    "run",
]
