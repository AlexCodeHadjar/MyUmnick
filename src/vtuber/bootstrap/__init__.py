"""Корень композиции: сборка графа объектов и точка входа."""

from vtuber.bootstrap.config import AppConfig, load_app_config
from vtuber.bootstrap.persona import PersonaConfig, load_persona

__all__ = ["AppConfig", "PersonaConfig", "load_app_config", "load_persona"]
