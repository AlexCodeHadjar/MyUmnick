"""Конфигурация приложения: секции модулей из config/*.toml и переменных VTUBER_*."""

from collections.abc import Mapping
from pathlib import Path

from pydantic import Field

from vtuber.adapters.gpu import NvidiaSmiConfig
from vtuber.adapters.llm import GenerationConfig, LLMConfig
from vtuber.adapters.memory import E5Config
from vtuber.adapters.stt import VadConfig, WhisperConfig
from vtuber.adapters.tts import TTSConfig
from vtuber.application.memory import FactMemoryConfig, RetrievalConfig
from vtuber.application.pipeline import PipelineConfig
from vtuber.application.prompting import ContextConfig
from vtuber.application.scheduler import ResourcesConfig, SchedulerConfig
from vtuber.application.voice import VoiceConfig
from vtuber.bootstrap.persona import PersonaConfig
from vtuber.gateway import GatewayConfig
from vtuber.kernel import (
    ConfigFiles,
    ConfigSection,
    LoggingConfig,
    PluginsConfig,
    TelemetryConfig,
    load_config,
)


class MemoryConfig(ConfigSection):
    """Секция `[memory]`: фоновая память (Этап 10) — факты и резюме истории в простое.

    `background_slot_id` — слот llama-server для фона: кэш диалога (слот 0) не трогается;
    `generation` — длина и температура фоновых запросов (низкая: факты и пересказ, не творчество).
    """

    enabled: bool
    store_path: Path
    background_slot_id: int = Field(ge=0)
    generation: GenerationConfig
    facts: FactMemoryConfig
    retrieval: RetrievalConfig
    e5: E5Config

    def resolved(self, root: Path) -> "MemoryConfig":
        """Копия с путями базы и модели от корня проекта."""
        return self.model_copy(
            update={
                "store_path": root / self.store_path,
                "e5": self.e5.model_copy(update={"model_dir": root / self.e5.model_dir}),
            }
        )


class SttConfig(ConfigSection):
    """Секция `[stt]`: голосовой ввод в `serve` (Этап 11, ADR-0016); модели — при первом кадре."""

    enabled: bool
    voice: VoiceConfig
    vad: VadConfig
    whisper: WhisperConfig

    def resolved(self, root: Path) -> "SttConfig":
        """Копия с путями моделей от корня проекта."""
        return self.model_copy(
            update={
                "vad": self.vad.model_copy(update={"model_path": root / self.vad.model_path}),
                "whisper": self.whisper.model_copy(
                    update={"model_dir": root / self.whisper.model_dir}
                ),
            }
        )


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
    scheduler: SchedulerConfig
    memory: MemoryConfig
    stt: SttConfig
    plugins: PluginsConfig
    resources: ResourcesConfig
    gpu_probe: NvidiaSmiConfig


def load_app_config(root: Path, env: Mapping[str, str]) -> AppConfig:
    """Читает `config/default.toml` и `config/user.toml` из корня проекта `root` поверх `env`.

    Raises:
        ConfigError: см. `vtuber.kernel.load_config`.

    """
    config_dir = root / "config"
    files = ConfigFiles(default=config_dir / "default.toml", user=config_dir / "user.toml")
    return load_config(AppConfig, files, env)
