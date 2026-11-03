"""Снимок менеджера доходит до панели по WebSocket; закрытая панель ничего не получает."""

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from websockets.asyncio.client import ClientConnection, connect

from tests.fakes import FakeClock, FakeLLM
from tests.fakes.conversation import make_conversation
from vtuber.application.scheduler import ModelSpec, Priority, ResourceManager, ResourcesConfig
from vtuber.gateway import GatewayConfig, GatewayServer, ResourcesFeed
from vtuber.kernel import EventBus, Telemetry

PERIOD_S = 0.02


def _watch(*, enabled: bool) -> str:
    return json.dumps({"v": 1, "type": "resources.watch", "data": {"enabled": enabled}})


class _Model:
    async def load(self) -> None:
        await asyncio.sleep(0)

    async def unload(self) -> None:
        await asyncio.sleep(0)


def _manager(wait_timeout_s: float = 2.0) -> ResourceManager:
    cfg = ResourcesConfig(
        total_vram_mb=16000,
        system_reserve_mb=1000,
        wait_timeout_s=wait_timeout_s,
        keep_loaded_s=100,
        gpu_poll_s=0,
        gpu_margin_mb=0,
        max_tool_mb=5000,
        max_background_mb=3000,
        pinned={"llm": 11000},
    )
    return ResourceManager(cfg)


async def _next_snapshot(ws: ClientConnection) -> dict[str, object]:
    while True:
        message = json.loads(await asyncio.wait_for(ws.recv(), 2))
        if message["type"] == "resources.snapshot":
            data: dict[str, object] = message["data"]
            return data


async def _quiet(ws: ClientConnection) -> bool:
    try:
        while True:
            message = json.loads(await asyncio.wait_for(ws.recv(), PERIOD_S * 5))
            if message["type"] == "resources.snapshot":
                return False
    except TimeoutError:
        return True


@asynccontextmanager
async def _panel(manager: ResourceManager) -> AsyncIterator[tuple[ClientConnection, ResourcesFeed]]:
    bus = EventBus()
    service = make_conversation(FakeLLM("Ок"), bus, Telemetry(bus, FakeClock()))
    cfg = GatewayConfig(host="127.0.0.1", port=0)
    async with GatewayServer(service, bus, cfg) as server:
        feed = ResourcesFeed(manager.snapshot, server.send, PERIOD_S)
        server.use_resources(feed)
        async with connect(f"ws://127.0.0.1:{server.port}") as ws:
            yield ws, feed


async def _stopped(feed: ResourcesFeed) -> bool:
    for _ in range(50):
        if not feed.running:
            return True
        await asyncio.sleep(PERIOD_S)
    return False


async def test_panel_gets_snapshots_only_while_open() -> None:
    async with _panel(_manager()) as (ws, feed):
        assert await _quiet(ws)
        await ws.send(_watch(enabled=True))
        first = await _next_snapshot(ws)
        assert first["pinned"] == [{"name": "llm", "vram_mb": 11000}]
        assert first["free_mb"] == 4000
        await ws.send(_watch(enabled=False))
        assert await _stopped(feed)
        await asyncio.sleep(PERIOD_S * 2)
        assert await _quiet(ws)


async def test_new_model_appears_in_snapshot_with_its_state() -> None:
    manager = _manager()
    manager.register(ModelSpec("код", 3000, Priority.TOOL), _Model())
    async with _panel(manager) as (ws, _):
        await ws.send(_watch(enabled=True))
        await _next_snapshot(ws)
        manager.register(ModelSpec("слух", 500, Priority.BACKGROUND), _Model())
        async with manager.use("код"):
            seen = await _next_snapshot(ws)
            while len(seen["models"]) < 2 or seen["free_mb"] != 1000:  # type: ignore[arg-type]
                seen = await _next_snapshot(ws)
    models = {m["name"]: m for m in seen["models"]}  # type: ignore[attr-defined]
    assert models["код"]["state"] == "in_use"
    assert models["код"]["priority"] == "tool"
    assert models["слух"]["state"] == "unloaded"


async def test_client_gone_stops_snapshots() -> None:
    async with _panel(_manager()) as (ws, feed):
        await ws.send(_watch(enabled=True))
        await _next_snapshot(ws)
        await ws.close()
        assert await _stopped(feed)


async def test_waiting_model_shows_reason() -> None:
    manager = _manager(wait_timeout_s=1.0)
    manager.register(ModelSpec("занята", 3000, Priority.TOOL), _Model())
    manager.register(ModelSpec("ждёт", 3000, Priority.TOOL), _Model())
    release = asyncio.Event()

    async def hold() -> None:
        async with manager.use("занята"):
            await release.wait()

    async def wait() -> None:
        async with manager.use("ждёт"):
            await asyncio.sleep(0)

    holding = asyncio.create_task(hold())
    await asyncio.sleep(0.01)
    waiting = asyncio.create_task(wait())
    await asyncio.sleep(0.01)
    status = {m.spec.name: m for m in manager.snapshot().models}
    assert status["ждёт"].state.value == "waiting"
    assert status["ждёт"].waiting_reason == "не хватает видеопамяти"
    assert status["занята"].waiting_reason is None
    release.set()
    await asyncio.gather(holding, waiting)
