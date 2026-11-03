"""Лимиты по фактической видеопамяти: фейковая видеокарта, сторонняя программа, ограничения."""

import asyncio
from dataclasses import dataclass

import pytest

from vtuber.adapters.gpu import parse_memory
from vtuber.application.scheduler import ModelSpec, Priority, ResourceManager, ResourcesConfig
from vtuber.domain import GpuMemory, ResourceUnavailable, TurnFinished, TurnId, TurnStarted
from vtuber.kernel import EventBus

TOTAL_MB = 16000
TURN = TurnId(1)
TICK_S = 0.01


@dataclass(slots=True)
class _Gpu:
    """Фейковая видеокарта: основная модель и сторонние программы плюс наши загруженные модели."""

    other_mb: int = 10000
    ours_mb: int = 0
    polls: int = 0
    works: bool = True

    async def memory(self) -> GpuMemory | None:
        self.polls += 1
        if not self.works:
            return None
        return GpuMemory(TOTAL_MB, self.other_mb + self.ours_mb)


class _Model:
    def __init__(self, gpu: _Gpu, vram_mb: int, log: list[str], name: str) -> None:
        self._gpu = gpu
        self._vram_mb = vram_mb
        self._log = log
        self._name = name

    async def load(self) -> None:
        self._gpu.ours_mb += self._vram_mb
        self._log.append(f"load {self._name}")

    async def unload(self) -> None:
        self._gpu.ours_mb -= self._vram_mb
        self._log.append(f"unload {self._name}")


def _manager(**overrides: float) -> ResourceManager:
    values: dict[str, object] = {
        "total_vram_mb": TOTAL_MB,
        "system_reserve_mb": 1000,
        "wait_timeout_s": 2.0,
        "keep_loaded_s": 100.0,
        "gpu_poll_s": TICK_S,
        "gpu_margin_mb": 500,
        "max_tool_mb": 5000,
        "max_background_mb": 2000,
        "pinned": {"llm": 9000},
    }
    return ResourceManager(ResourcesConfig.model_validate({**values, **overrides}))


def _add(
    manager: ResourceManager,
    gpu: _Gpu,
    log: list[str],
    spec: tuple[str, int, Priority],
) -> None:
    name, vram_mb, priority = spec
    manager.register(ModelSpec(name, vram_mb, priority), _Model(gpu, vram_mb, log, name))


async def test_other_program_shrinks_limit_task_waits_and_resumes_when_freed() -> None:
    gpu = _Gpu(other_mb=14000)
    log: list[str] = []
    manager = _manager()
    _add(manager, gpu, log, ("фон", 1000, Priority.BACKGROUND))
    await manager.observe(await gpu.memory())
    assert manager.limit_mb() == 1500

    async def job() -> None:
        async with manager.use("фон"):
            log.append("фон работает")

    gpu.other_mb = 15000  # сторонняя программа заняла почти всё
    await manager.observe(await gpu.memory())
    waiting = asyncio.create_task(job())
    await asyncio.sleep(TICK_S)
    assert log == []
    gpu.other_mb = 12000  # программа закрылась
    await manager.observe(await gpu.memory())
    await asyncio.wait_for(waiting, 1)
    assert log == ["load фон", "фон работает"]


async def test_shrunk_limit_evicts_idle_lowest_priority_first() -> None:
    gpu = _Gpu(other_mb=9000)
    log: list[str] = []
    manager = _manager()
    _add(manager, gpu, log, ("инструмент", 2000, Priority.TOOL))
    _add(manager, gpu, log, ("фон", 2000, Priority.BACKGROUND))
    await manager.observe(await gpu.memory())
    async with manager.use("инструмент"):
        pass
    async with manager.use("фон"):
        pass
    gpu.other_mb = 12000  # места хватает только на одну модель
    await manager.observe(await gpu.memory())
    assert log == ["load инструмент", "load фон", "unload фон"]


async def test_model_in_use_is_not_stopped_when_limit_shrinks() -> None:
    gpu = _Gpu()
    log: list[str] = []
    manager = _manager()
    _add(manager, gpu, log, ("инструмент", 3000, Priority.TOOL))
    async with manager.use("инструмент"):
        gpu.other_mb = 15000
        await manager.observe(await gpu.memory())
        assert log == ["load инструмент"]


@pytest.mark.parametrize(
    "spec",
    [
        ("большой инструмент", 5001, Priority.TOOL),
        ("большой фон", 2001, Priority.BACKGROUND),
    ],
)
async def test_model_above_its_limit_is_refused_at_once(spec: tuple[str, int, Priority]) -> None:
    gpu = _Gpu(other_mb=0)
    log: list[str] = []
    manager = _manager()
    _add(manager, gpu, log, spec)
    with pytest.raises(ResourceUnavailable, match="ограничен"):
        async with manager.use(spec[0]):
            pass
    assert log == []


async def test_background_total_never_exceeds_limit() -> None:
    gpu = _Gpu(other_mb=0)
    log: list[str] = []
    manager = _manager(wait_timeout_s=0.05)
    _add(manager, gpu, log, ("фон 1", 1500, Priority.BACKGROUND))
    _add(manager, gpu, log, ("фон 2", 1500, Priority.BACKGROUND))
    async with manager.use("фон 1"):
        with pytest.raises(ResourceUnavailable):
            async with manager.use("фон 2"):
                pass
    # Простаивающая фоновая модель уступает место другой фоновой, сумма остаётся в лимите.
    async with manager.use("фон 2"):
        pass
    assert log == ["load фон 1", "unload фон 1", "load фон 2"]


async def test_static_budget_still_limits_when_card_looks_free() -> None:
    gpu = _Gpu(other_mb=0)
    manager = _manager()
    await manager.observe(await gpu.memory())
    assert manager.limit_mb() == 16000 - 1000 - 9000


async def test_failed_probe_falls_back_to_config_limits() -> None:
    gpu = _Gpu(other_mb=15000)
    manager = _manager()
    await manager.observe(await gpu.memory())
    assert manager.limit_mb() == 500
    await manager.observe(None)
    assert manager.limit_mb() == 6000


async def test_watch_does_not_poll_during_dialog_turn() -> None:
    gpu = _Gpu()
    bus = EventBus()
    manager = _manager()
    manager.follow(bus)
    await bus.publish(TurnStarted(TURN))
    watching = asyncio.create_task(manager.watch(gpu))
    await asyncio.sleep(TICK_S * 5)
    assert gpu.polls == 0
    await bus.publish(TurnFinished(TURN))
    await asyncio.sleep(TICK_S * 5)
    watching.cancel()
    assert gpu.polls > 0


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ("16384, 8900\n", GpuMemory(16384, 8900)),
        ("16384, 8900\n8192, 100\n", GpuMemory(16384, 8900)),
        ("[N/A], [N/A]\n", None),
        ("", None),
    ],
)
def test_parse_nvidia_smi_output(output: str, expected: GpuMemory | None) -> None:
    assert parse_memory(output) == expected
