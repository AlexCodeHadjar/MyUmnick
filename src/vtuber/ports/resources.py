"""Порт модели под управлением менеджера ресурсов (ADR-0017): отдельный процесс или библиотека."""

from typing import Protocol

from vtuber.domain import GpuMemory


class ManagedModel(Protocol):
    """Модель, которую можно загрузить в видеопамять и выгрузить по требованию."""

    async def load(self) -> None:
        """Загрузить; при сбое или отмене убрать за собой и не держать память."""

    async def unload(self) -> None:
        """Выгрузить и освободить видеопамять."""


class GpuProbe(Protocol):
    """Фактическая занятость видеопамяти (ADR-0018)."""

    async def memory(self) -> GpuMemory | None:
        """Текущее состояние; None — узнать нельзя, работаем по лимитам конфига."""
