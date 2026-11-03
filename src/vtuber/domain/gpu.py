"""Состояние видеопамяти (ADR-0018)."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GpuMemory:
    """Сколько видеопамяти всего и сколько занято всеми программами."""

    total_mb: int
    used_mb: int
