"""Конфигурация приложения: секции модулей из config/*.toml и переменных VTUBER_*."""

from collections.abc import Mapping
from pathlib import Path

from vtuber.adapters.llm import LLMConfig
from vtuber.adapters.tts import TTSConfig
from vtuber.application.pipeline import PipelineConfig
from vtuber.application.prompting import ContextConfig
from vtuber.bootstrap.persona import PersonaConfig
from vtuber.gateway import GatewayConfig
from vtuber.kernel import ConfigFiles, ConfigSection, LoggingConfig, TelemetryConfig, load_config


class AppConfig(ConfigSection):
    """Корень конфига. Только агрегирует: каждую секцию описывает модуль, которому она нужна."""

    logging: LoggingConfig
    telemetry: TelemetryConfig
    llm: LLMConfig
    persona: PersonaConfig
    context: ContextConfig
    gateway: GatewayConfig
    pipeline: PipelineConfig
    tts: TTSConfig


def load_app_config(root: Path, env: Mapping[str, str]) -> AppConfig:
    """Читает `config/default.toml` и `config/user.toml` из корня проекта `root` поверх `env`.

    Raises:
        ConfigError: см. `vtuber.kernel.load_config`.

    """
    config_dir = root / "config"
    files = ConfigFiles(default=config_dir / "default.toml", user=config_dir / "user.toml")
    return load_config(AppConfig, files, env)
