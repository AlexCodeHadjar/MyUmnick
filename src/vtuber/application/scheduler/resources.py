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
from types import TracebackType
from typing import Self

from vtuber.application.scheduler.resource_types import (
    ModelSpec,
    ModelState,
    ModelStatus,
    Priority,
    ResourcesConfig,
)
from vtuber.domain import (
    ConfigError,
    GpuMemory,
    ResourceUnavailable,
    TurnCancelled,
    TurnFinished,
    TurnStarted,
)
from vtuber.kernel import EventBus, get_logger
from vtuber.ports import GpuProbe, ManagedModel

_log = get_logger(__name__)


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
        self._others_mb: int | None = None
        self._card_mb = cfg.total_vram_mb
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
        """Лимит незакреплённых моделей по конфигу; `limit_mb` учитывает и саму видеокарту."""
        return self._capacity_mb

    def limit_mb(self) -> int:
        """Лимит сейчас: по конфигу, но не больше того, что другие программы оставили на карте."""
        if self._others_mb is None:
            return self._capacity_mb
        left = self._card_mb - self._others_mb - self._cfg.gpu_margin_mb
        return max(0, min(self._capacity_mb, left))

    async def observe(self, memory: GpuMemory | None) -> None:
        """Новый замер: лимит сжался — простаивающие модели уходят; вырос — ожидающие идут."""
        loaded = sum(e.spec.vram_mb for e in self._entries.values() if e.loaded)
        if memory is None:
            self._others_mb = None
        else:
            self._others_mb = max(0, memory.used_mb - loaded)
            self._card_mb = memory.total_mb
        async with self._transition:
            for entry in self._evictable(Priority.TOOL):
                if self._free_mb() >= 0:
                    break
                await self._unload(entry)
        self._changed.set()

    async def watch(self, probe: GpuProbe) -> None:
        """Опрашивает карту, пока задачу не отменят; во время хода не трогает её совсем (T-11)."""
        while True:
            await asyncio.sleep(self._cfg.gpu_poll_s)
            if not self._dialog_active:
                await self.observe(await probe.memory())

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
        self._refuse_if_never_fits(entry)
        await self._claim_within_timeout(entry)
        try:
            yield
        finally:
            entry.users -= 1
            entry.last_used = self._clock()
            self._changed.set()

    def _refuse_if_never_fits(self, entry: _Entry) -> None:
        spec = entry.spec
        if spec.vram_mb > self._capacity_mb:
            msg = (
                f"Модели '{spec.name}' нужно {spec.vram_mb} МБ видеопамяти, а после основной "
                f"модели и голоса остаётся {self._capacity_mb} МБ"
            )
            raise ResourceUnavailable(msg)
        limit = self._priority_limit(spec.priority)
        if spec.vram_mb > limit:
            msg = f"Модели '{spec.name}' нужно {spec.vram_mb} МБ, а её вид ограничен {limit} МБ"
            raise ResourceUnavailable(msg)

    def _priority_limit(self, priority: Priority) -> int:
        if priority is Priority.BACKGROUND:
            return self._cfg.max_background_mb
        return self._cfg.max_tool_mb

    async def trim(self) -> None:
        """Выгрузить модели, которые простаивают дольше `keep_loaded_s`."""
        oldest_allowed = self._clock() - self._cfg.keep_loaded_s
        async with self._transition:
            for entry in self._entries.values():
                if entry.evictable and entry.last_used <= oldest_allowed:
                    await self._unload(entry)
        self._changed.set()

    async def run(self, probe: GpuProbe) -> None:
        """Выгрузка простаивающих и опрос карты, пока задачу не отменят (владелец — bootstrap)."""
        async with asyncio.TaskGroup() as tg:
            if self._cfg.gpu_poll_s > 0:
                tg.create_task(self.watch(probe))
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
        return entry.loaded or self._has_room(entry)

    def _has_room(self, entry: _Entry) -> bool:
        need = entry.spec.vram_mb
        if self._busy_background_mb(entry) + need > self._background_room(entry):
            return False
        return self._free_after_eviction(entry.spec.priority) >= need

    def _free_mb(self) -> int:
        used = sum(e.spec.vram_mb for e in self._entries.values() if e.loaded)
        return self.limit_mb() - used

    def _background_room(self, entry: _Entry) -> int:
        """Инструмента общий лимит фона не касается."""
        if entry.spec.priority is Priority.BACKGROUND:
            return self._cfg.max_background_mb
        return self._capacity_mb

    def _busy_background_mb(self, entry: _Entry) -> int:
        if entry.spec.priority is not Priority.BACKGROUND:
            return 0
        running = (e for e in self._entries.values() if e.loaded and e.users)
        return sum(e.spec.vram_mb for e in running if e.spec.priority is Priority.BACKGROUND)

    def _background_loaded_mb(self) -> int:
        loaded = (e for e in self._entries.values() if e.loaded)
        return sum(e.spec.vram_mb for e in loaded if e.spec.priority is Priority.BACKGROUND)

    def _free_after_eviction(self, priority: Priority) -> int:
        return self._free_mb() + sum(e.spec.vram_mb for e in self._evictable(priority))

    def _evictable(self, priority: Priority) -> list[_Entry]:
        """Простаивающие модели не важнее `priority`: сначала менее важные, затем давние."""
        found = [e for e in self._entries.values() if e.evictable and e.spec.priority <= priority]
        return sorted(found, key=lambda e: (e.spec.priority, e.last_used))

    async def _bring_up(self, entry: _Entry) -> None:
        if not entry.loaded:
            for victim in self._evictable(entry.spec.priority):
                if not self._needs_room(entry):
                    break
                await self._unload(victim)
            await self._load(entry)
        entry.users += 1

    def _needs_room(self, entry: _Entry) -> bool:
        if self._free_mb() < entry.spec.vram_mb:
            return True
        over = self._background_loaded_mb() + entry.spec.vram_mb > self._cfg.max_background_mb
        return entry.spec.priority is Priority.BACKGROUND and over

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
