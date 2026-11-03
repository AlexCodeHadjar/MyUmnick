"""Менеджер ресурсов на фейках: нехватка памяти не вытесняет закреплённое, приоритет соблюдается."""

import asyncio
from collections.abc import Coroutine

import pytest

from vtuber.application.scheduler import (
    ModelSpec,
    ModelState,
    Priority,
    ResourceManager,
    ResourcesConfig,
)
from vtuber.domain import ConfigError, ResourceUnavailable, TurnFinished, TurnId, TurnStarted
from vtuber.kernel import EventBus

TURN = TurnId(1)


class _Model:
    def __init__(self, log: list[str], name: str, *, broken: bool = False) -> None:
        self._log = log
        self._name = name
        self._broken = broken

    async def load(self) -> None:
        if self._broken:
            raise RuntimeError("нет файла")
        self._log.append(f"load {self._name}")

    async def unload(self) -> None:
        self._log.append(f"unload {self._name}")


class _Time:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _manager(
    *, free_mb: int = 4000, timeout_s: float = 0.05, clock: _Time | None = None
) -> ResourceManager:
    cfg = ResourcesConfig(
        total_vram_mb=16000,
        system_reserve_mb=1000,
        wait_timeout_s=timeout_s,
        keep_loaded_s=10.0,
        gpu_poll_s=0,
        gpu_margin_mb=0,
        max_tool_mb=15000,
        max_background_mb=15000,
        pinned={"llm": 15000 - free_mb},
    )
    return ResourceManager(cfg) if clock is None else ResourceManager(cfg, clock)


def _add(
    manager: ResourceManager,
    log: list[str],
    name: str,
    vram_mb: int,
    priority: Priority = Priority.TOOL,
) -> None:
    manager.register(ModelSpec(name, vram_mb, priority), _Model(log, name))


async def _settle() -> None:
    for _ in range(10):
        await asyncio.sleep(0)


async def _started(job: Coroutine[None, None, None]) -> asyncio.Task[None]:
    task = asyncio.create_task(job)
    await _settle()
    return task


def test_pinned_above_budget_is_a_config_error() -> None:
    cfg = ResourcesConfig(
        total_vram_mb=8000,
        system_reserve_mb=1000,
        wait_timeout_s=1,
        keep_loaded_s=1,
        gpu_poll_s=0,
        gpu_margin_mb=0,
        max_tool_mb=1,
        max_background_mb=1,
        pinned={"llm": 8700},
    )
    with pytest.raises(ConfigError, match="pinned"):
        ResourceManager(cfg)


async def test_model_loads_on_demand_and_stays_for_next_use() -> None:
    log: list[str] = []
    manager = _manager()
    _add(manager, log, "код", 3000)
    assert manager.snapshot().models[0].state is ModelState.UNLOADED
    async with manager.use("код"):
        assert manager.snapshot().models[0].state is ModelState.IN_USE
    assert manager.snapshot().models[0].state is ModelState.IDLE
    async with manager.use("код"):
        pass
    assert log == ["load код"]


async def test_too_big_model_is_refused_at_once_without_touching_others() -> None:
    log: list[str] = []
    manager = _manager()
    _add(manager, log, "малая", 1000)
    _add(manager, log, "огромная", 5000)
    async with manager.use("малая"):
        pass
    with pytest.raises(ResourceUnavailable, match="5000 МБ"):
        async with manager.use("огромная"):
            pass
    assert log == ["load малая"]


async def test_idle_model_is_evicted_when_room_is_needed() -> None:
    log: list[str] = []
    manager = _manager()
    _add(manager, log, "первая", 3000)
    _add(manager, log, "вторая", 3000)
    async with manager.use("первая"):
        pass
    async with manager.use("вторая"):
        pass
    assert log == ["load первая", "unload первая", "load вторая"]


async def test_model_in_use_is_not_evicted_and_new_one_is_refused_after_waiting() -> None:
    log: list[str] = []
    manager = _manager()
    _add(manager, log, "работает", 3000)
    _add(manager, log, "ждёт", 3000)
    async with manager.use("работает"):
        with pytest.raises(ResourceUnavailable, match="не дождалась"):
            async with manager.use("ждёт"):
                pass
    assert log == ["load работает"]


async def test_waiting_task_starts_when_memory_is_released() -> None:
    log: list[str] = []
    manager = _manager(timeout_s=2)
    _add(manager, log, "работает", 3000)
    _add(manager, log, "ждёт", 3000)
    release = asyncio.Event()

    async def first() -> None:
        async with manager.use("работает"):
            await release.wait()

    async def second() -> None:
        async with manager.use("ждёт"):
            log.append("вторая работает")

    running = asyncio.create_task(first())
    await _settle()
    waiting = asyncio.create_task(second())
    await _settle()
    assert "вторая работает" not in log
    release.set()
    await asyncio.gather(running, waiting)
    assert log == ["load работает", "unload работает", "load ждёт", "вторая работает"]


async def test_tool_goes_before_background_waiting_for_the_same_memory() -> None:
    log: list[str] = []
    manager = _manager(timeout_s=0.2)
    _add(manager, log, "занята", 3000)
    _add(manager, log, "фон", 3000, Priority.BACKGROUND)
    _add(manager, log, "инструмент", 3000)
    release = asyncio.Event()

    async def hold() -> None:
        async with manager.use("занята"):
            await release.wait()

    async def job(name: str) -> None:
        try:
            async with manager.use(name):
                log.append(f"run {name}")
        except ResourceUnavailable:
            log.append(f"refused {name}")

    tasks = [await _started(hold()), await _started(job("фон")), await _started(job("инструмент"))]
    release.set()
    await asyncio.gather(*tasks)
    # Инструмент прошёл первым, а его простаивающую модель фон вытеснить не вправе.
    assert log[-2:] == ["run инструмент", "refused фон"]


async def test_background_cannot_evict_idle_tool_model() -> None:
    log: list[str] = []
    manager = _manager()
    _add(manager, log, "инструмент", 3000)
    _add(manager, log, "фон", 3000, Priority.BACKGROUND)
    async with manager.use("инструмент"):
        pass
    with pytest.raises(ResourceUnavailable):
        async with manager.use("фон"):
            pass
    assert log == ["load инструмент"]


async def test_background_waits_while_dialog_turn_is_running() -> None:
    log: list[str] = []
    bus = EventBus()
    manager = _manager(timeout_s=2)
    manager.follow(bus)
    _add(manager, log, "фон", 1000, Priority.BACKGROUND)
    _add(manager, log, "инструмент", 1000)

    async def background() -> None:
        async with manager.use("фон"):
            log.append("фон работает")

    await bus.publish(TurnStarted(TURN))
    waiting = asyncio.create_task(background())
    await _settle()
    assert log == []
    async with manager.use("инструмент"):  # инструмент идёт: его просят из самого хода
        pass
    assert "фон работает" not in log
    await bus.publish(TurnFinished(TURN))
    await waiting
    assert "фон работает" in log


async def test_failed_load_is_clear_refusal_and_does_not_count_memory() -> None:
    log: list[str] = []
    manager = _manager()
    manager.register(ModelSpec("битая", 3000, Priority.TOOL), _Model(log, "битая", broken=True))
    _add(manager, log, "целая", 3000)
    with pytest.raises(ResourceUnavailable, match="не загрузилась"):
        async with manager.use("битая"):
            pass
    async with manager.use("целая"):
        pass
    assert log == ["load целая"]


async def test_trim_unloads_only_long_idle_models() -> None:
    log: list[str] = []
    clock = _Time()
    manager = _manager(clock=clock)
    _add(manager, log, "давняя", 1000)
    _add(manager, log, "свежая", 1000)
    async with manager.use("давняя"):
        pass
    clock.now = 8.0
    async with manager.use("свежая"):
        pass
    clock.now = 11.0
    await manager.trim()
    assert log == ["load давняя", "load свежая", "unload давняя"]


async def test_closing_unloads_everything() -> None:
    log: list[str] = []
    async with _manager() as manager:
        _add(manager, log, "модель", 1000)
        async with manager.use("модель"):
            pass
    assert log == ["load модель", "unload модель"]


async def test_duplicate_name_is_a_config_error() -> None:
    manager = _manager()
    _add(manager, [], "модель", 1000)
    with pytest.raises(ConfigError, match="уже на учёте"):
        _add(manager, [], "модель", 1000)
