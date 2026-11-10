"""Конфигурация приложения: секции модулей из config/*.toml и переменных VTUBER_*."""

from collections.abc import Mapping
from pathlib import Path

from pydantic import Field, PrivateAttr

from vtuber.adapters.gpu import NvidiaSmiConfig
from vtuber.adapters.llm import GenerationConfig, LlamaServerConfig, LLMConfig
from vtuber.adapters.memory import E5Config
from vtuber.adapters.stt import SenseVoiceConfig, SpeakerModelConfig, VadConfig, WhisperConfig
from vtuber.adapters.tts import TTSConfig
from vtuber.application.conversation import InitiativeConfig
from vtuber.application.memory import FactMemoryConfig, RetrievalConfig
from vtuber.application.pipeline import PipelineConfig
from vtuber.application.prompting import ContextConfig
from vtuber.application.scheduler import ResourcesConfig, SchedulerConfig
from vtuber.application.supervision import SupervisorConfig
from vtuber.application.voice import AddressingConfig, SoundsConfig, SpeakersConfig, VoiceConfig
from vtuber.bootstrap.edition import EditionConfig, check_edition, edition_files, resolve_edition
from vtuber.bootstrap.persona import PersonaConfig
from vtuber.bootstrap.setup import SetupConfig
from vtuber.domain import EditionId
from vtuber.gateway import GatewayConfig
from vtuber.kernel import (
    ConfigSection,
    LoggingConfig,
    PluginsConfig,
    TelemetryConfig,
    load_config,
)


def _for_profile(store: Path, profile: str) -> Path:
    """Свой индекс на профиль; без профиля путь прежний, поэтому старые данные на месте."""
    return store.with_stem(f"{store.stem}-{profile}") if profile else store


class MemoryConfig(ConfigSection):
    """Секция `[memory]`: фоновая память (Этап 10) — факты и резюме истории в простое.

    `background_slot_id` — слот llama-server для фона: кэш диалога (слот 0) не трогается;
    `generation` — длина и температура фоновых запросов (низкая: факты и пересказ, не творчество).
    """

    enabled: bool
    store_path: Path
    vault_path: Path
    inbox: Path
    transfer_to: Path
    profile: str
    restore_turns: int = Field(ge=0)
    vault_poll_s: float = Field(gt=0)
    background_slot_id: int = Field(ge=0)
    generation: GenerationConfig
    facts: FactMemoryConfig
    retrieval: RetrievalConfig
    e5: E5Config
    # Исходная секция и корень: из них память любого чата получает свои пути (Этап 21).
    _source: "MemoryConfig | None" = PrivateAttr(default=None)
    _root: Path | None = PrivateAttr(default=None)

    def resolved(self, root: Path) -> "MemoryConfig":
        """Копия с путями базы и модели от корня проекта."""
        if self.profile in {".", ".."} or "/" in self.profile or "\\" in self.profile:
            msg = f"Имя профиля памяти — не путь: {self.profile}"
            raise ValueError(msg)
        copy = self.model_copy(
            update={
                "store_path": root / _for_profile(self.store_path, self.profile),
                "vault_path": root / (self.vault_path / self.profile),
                "inbox": root / self.inbox,
                "transfer_to": root / self.transfer_to,
                "e5": self.e5.model_copy(update={"model_dir": root / self.e5.model_dir}),
            }
        )
        copy._source = self  # noqa: SLF001 — свой класс
        copy._root = root  # noqa: SLF001
        return copy

    def with_profile(self, profile: str) -> "MemoryConfig":
        """Та же память с другим профилем (своя база и заметки), пути — от того же корня.

        Raises:
            ValueError: секция ещё не прошла `resolved`.

        """
        if self._source is None or self._root is None:
            msg = "with_profile — только после resolved()"
            raise ValueError(msg)
        return self._source.model_copy(update={"profile": profile}).resolved(self._root)


class SttConfig(ConfigSection):
    """Секция `[stt]`: голосовой ввод в `serve` (Этап 11, ADR-0016); модели — при первом кадре."""

    enabled: bool
    voice: VoiceConfig
    addressing: AddressingConfig
    sounds: SoundsConfig
    sound_model: SenseVoiceConfig
    speakers: SpeakersConfig
    speaker_model: SpeakerModelConfig
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
                "speaker_model": self.speaker_model.model_copy(
                    update={"model_path": root / self.speaker_model.model_path}
                ),
                "sound_model": self.sound_model.model_copy(
                    update={
                        "model_path": root / self.sound_model.model_path,
                        "tokens_path": root / self.sound_model.tokens_path,
                    }
                ),
            }
        )


class AppConfig(ConfigSection):
    """Корень конфига. Только агрегирует: каждую секцию описывает модуль, которому она нужна."""

    edition: EditionConfig
    logging: LoggingConfig
    telemetry: TelemetryConfig
    llm: LLMConfig
    llama_server: LlamaServerConfig
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
    setup: SetupConfig
    supervisor: SupervisorConfig
    initiative: InitiativeConfig


def load_app_config(
    root: Path, env: Mapping[str, str], edition: EditionId | None = None
) -> AppConfig:
    """Читает конфиг издания из `<root>/config` поверх `env` (порядок — `edition_files`).

    Издание — `edition`, иначе `VTUBER_EDITION__ID` из `env`, иначе `ru`: так инструменты
    (`tools/*`) работают с любым изданием без своего аргумента.

    Raises:
        ConfigError: см. `vtuber.kernel.load_config`; `[edition].id` не совпал с `edition`.

    """
    chosen = edition if edition is not None else resolve_edition(None, env)
    cfg = load_config(AppConfig, edition_files(root / "config", chosen), env)
    check_edition(cfg.edition, chosen)
    return cfg
