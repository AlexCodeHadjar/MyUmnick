"""Значения менеджера ресурсов (ADR-0017, ADR-0018): настройки, приоритеты, снимок моделей."""

from dataclasses import dataclass
from enum import IntEnum, StrEnum

from pydantic import Field

from vtuber.kernel import ConfigSection


class ResourcesConfig(ConfigSection):
    """Секция `[resources]`: бюджет видеопамяти; `pinned` — имя → МБ, не вытесняется никогда."""

    total_vram_mb: int = Field(gt=0)
    system_reserve_mb: int = Field(ge=0)
    wait_timeout_s: float = Field(gt=0)
    keep_loaded_s: float = Field(gt=0)
    gpu_poll_s: float = Field(ge=0)
    gpu_margin_mb: int = Field(ge=0)
    max_tool_mb: int = Field(gt=0)
    max_background_mb: int = Field(gt=0)
    pinned: dict[str, int]


class Priority(IntEnum):
    """Кто важнее при нехватке памяти; диалог закреплён и в очереди не стоит."""

    BACKGROUND = 0
    TOOL = 1


class ModelState(StrEnum):
    """Что с моделью сейчас."""

    UNLOADED = "unloaded"
    IDLE = "idle"
    IN_USE = "in_use"


@dataclass(frozen=True, slots=True)
class ModelSpec:
    """Модель под управлением: `vram_mb` — объём из замера (ADR-0017)."""

    name: str
    vram_mb: int
    priority: Priority


@dataclass(frozen=True, slots=True)
class ModelStatus:
    """Снимок одной модели для панели ресурсов."""

    spec: ModelSpec
    state: ModelState
    users: int
