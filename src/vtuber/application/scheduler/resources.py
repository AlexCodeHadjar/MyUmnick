"""Менеджер ресурсов моделей (ADR-0017): учёт VRAM, загрузка по требованию, приоритет диалога.

Закреплённое (основная LLM, голос) вычитается из бюджета сразу и не вытесняется ничем. Остальные
модели грузятся на время использования и остаются в памяти про запас, пока место не понадобится.
Не хватает места — задача ждёт, а когда ждать бессмысленно или срок вышел, получает понятный отказ.
"""

import asyncio
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import IntEnum, StrEnum
from types import TracebackType
from typing import Self

from pydantic import Field

from vtuber.domain import (
    ConfigError,
    ResourceUnavailable,
    TurnCancelled,
    TurnFinished,
    TurnStarted,
)
from vtuber.kernel import ConfigSection, EventBus, get_logger
from vtuber.ports import ManagedModel

_log = get_logger(__name__)


class ResourcesConfig(ConfigSection):
    """Секция `[resources]`: бюджет видеопамяти; `pinned` — имя → МБ, не вытесняется никогда."""

    total_vram_mb: int = Field(gt=0)
    system_reserve_mb: int = Field(ge=0)
    wait_timeout_s: float = Field(gt=0)
    keep_loaded_s: float = Field(gt=0)
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


@dataclass(slots=True)
class _Entry:
    spec: ModelSpec
    model: ManagedModel
    loaded: bool = False
    users: int = 0
    last_used: float = 0.0

    @property
    def evictable(self) -> bool:
        return self.loaded and self.users == 0


class ResourceManager:
    """Единственное место, которое решает, какая модель сейчас в видеопамяти."""

    def __init__(self, cfg: ResourcesConfig, clock: Callable[[], float] = time.monotonic) -> None:
        self._cfg = cfg
        self._clock = clock
        self._capacity_mb = cfg.total_vram_mb - cfg.system_reserve_mb - sum(cfg.pinned.values())
        if self._capacity_mb < 0:
            msg = (
                f"[resources]: закреплено больше видеопамяти, чем есть (не хватает "
                f"{-self._capacity_mb} МБ) — уменьшите pinned или system_reserve_mb"
            )
            raise ConfigError(msg)
        self._entries: dict[str, _Entry] = {}
        self._transition = asyncio.Lock()
        self._changed = asyncio.Event()
        self._waiting: list[Priority] = []
        self._dialog_active = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        for entry in self._entries.values():
            if entry.loaded:
                await self._unload(entry)

    @property
    def capacity_mb(self) -> int:
        """Сколько видеопамяти доступно незакреплённым моделям."""
        return self._capacity_mb

    def register(self, spec: ModelSpec, model: ManagedModel) -> None:
        """Поставить модель на учёт; она не загружается, пока её не попросят.

        Raises:
            ConfigError: имя уже занято.

        """
        if spec.name in self._entries:
            msg = f"Модель '{spec.name}' уже на учёте — переименуйте одну из них"
            raise ConfigError(msg)
        self._entries[spec.name] = _Entry(spec, model)

    def follow(self, bus: EventBus) -> None:
        """Пока идёт ход диалога, новые фоновые задачи не начинаются."""
        bus.subscribe(TurnStarted, self._on_started)
        bus.subscribe(TurnFinished, self._on_ended)
        bus.subscribe(TurnCancelled, self._on_ended)

    def snapshot(self) -> tuple[ModelStatus, ...]:
        """Что сейчас с каждой моделью."""
        return tuple(
            ModelStatus(entry.spec, _state_of(entry), entry.users)
            for entry in self._entries.values()
        )

    @asynccontextmanager
    async def use(self, name: str) -> AsyncIterator[None]:
        """Модель `name` в памяти на время блока; несколько задач делят одну модель.

        Raises:
            ResourceUnavailable: модель не помещается, не загрузилась или не дождалась места.

        """
        entry = self._entries[name]
        if entry.spec.vram_mb > self._capacity_mb:
            msg = (
                f"Модели '{name}' нужно {entry.spec.vram_mb} МБ видеопамяти, а после основной "
                f"модели и голоса остаётся {self._capacity_mb} МБ"
            )
            raise ResourceUnavailable(msg)
        await self._claim_within_timeout(entry)
        try:
            yield
        finally:
            entry.users -= 1
            entry.last_used = self._clock()
            self._changed.set()

    async def trim(self) -> None:
        """Выгрузить модели, которые простаивают дольше `keep_loaded_s`."""
        oldest_allowed = self._clock() - self._cfg.keep_loaded_s
        async with self._transition:
            for entry in self._entries.values():
                if entry.evictable and entry.last_used <= oldest_allowed:
                    await self._unload(entry)
        self._changed.set()

    async def run(self) -> None:
        """Выгружает простаивающие модели, пока задачу не отменят (владелец — bootstrap)."""
        while True:
            await asyncio.sleep(self._cfg.keep_loaded_s / 2)
            await self.trim()

    async def _on_started(self, _: TurnStarted) -> None:
        self._dialog_active = True

    async def _on_ended(self, _: TurnFinished | TurnCancelled) -> None:
        self._dialog_active = False
        self._changed.set()

    async def _claim_within_timeout(self, entry: _Entry) -> None:
        try:
            async with asyncio.timeout(self._cfg.wait_timeout_s):
                await self._claim(entry)
        except TimeoutError as exc:
            msg = f"Модель '{entry.spec.name}' не дождалась видеопамяти или очереди загрузки"
            raise ResourceUnavailable(msg) from exc

    async def _claim(self, entry: _Entry) -> None:
        priority = entry.spec.priority
        self._waiting.append(priority)
        try:
            while True:
                async with self._transition:
                    if self._may_start(entry):
                        await self._bring_up(entry)
                        return
                self._changed.clear()
                await self._changed.wait()
        finally:
            self._waiting.remove(priority)
            self._changed.set()

    def _may_start(self, entry: _Entry) -> bool:
        priority = entry.spec.priority
        if priority is Priority.BACKGROUND and self._dialog_active:
            return False
        if any(other > priority for other in self._waiting):
            return False
        return entry.loaded or self._free_after_eviction(priority) >= entry.spec.vram_mb

    def _free_mb(self) -> int:
        used = sum(e.spec.vram_mb for e in self._entries.values() if e.loaded)
        return self._capacity_mb - used

    def _free_after_eviction(self, priority: Priority) -> int:
        return self._free_mb() + sum(e.spec.vram_mb for e in self._evictable(priority))

    def _evictable(self, priority: Priority) -> list[_Entry]:
        """Простаивающие модели не важнее `priority`: сначала менее важные, затем давние."""
        found = [e for e in self._entries.values() if e.evictable and e.spec.priority <= priority]
        return sorted(found, key=lambda e: (e.spec.priority, e.last_used))

    async def _bring_up(self, entry: _Entry) -> None:
        if not entry.loaded:
            for victim in self._evictable(entry.spec.priority):
                if self._free_mb() >= entry.spec.vram_mb:
                    break
                await self._unload(victim)
            await self._load(entry)
        entry.users += 1

    async def _load(self, entry: _Entry) -> None:
        _log.info("resources.load", model=entry.spec.name, vram_mb=entry.spec.vram_mb)
        try:
            await entry.model.load()
        except Exception as exc:
            msg = f"Модель '{entry.spec.name}' не загрузилась: {exc}"
            raise ResourceUnavailable(msg) from exc
        entry.loaded = True

    async def _unload(self, entry: _Entry) -> None:
        _log.info("resources.unload", model=entry.spec.name)
        entry.loaded = False
        try:
            await entry.model.unload()
        except Exception:  # noqa: BLE001 — R-42: чужая модель; учёт важнее, остальные ждут места
            _log.exception("resources.unload_failed", model=entry.spec.name)


def _state_of(entry: _Entry) -> ModelState:
    if not entry.loaded:
        return ModelState.UNLOADED
    return ModelState.IN_USE if entry.users else ModelState.IDLE
