import asyncio
import io
import json
from collections.abc import Iterable, Mapping
from importlib.metadata import EntryPoint
from pathlib import Path

import pytest

from vtuber.bootstrap.plugins import ENTRY_POINT_GROUP, running_plugins
from vtuber.domain import TurnFinished, TurnId
from vtuber.kernel import EventBus, LoggingConfig, PluginContext, PluginsConfig, logging_to

EVENT = TurnFinished(TurnId(1))
MODULE = __name__


class Recording:
    """Плагин: запоминает события и то, как его останавливали."""

    name = "recording"
    instances: list["Recording"] = []  # noqa: RUF012 — экземпляр создаёт загрузчик, тест его ищет

    def __init__(self) -> None:
        self.events: list[TurnFinished] = []
        self.stopped = False
        Recording.instances.append(self)

    async def setup(self, ctx: PluginContext) -> None:
        ctx.subscribe(TurnFinished, self._on_turn)

    async def shutdown(self) -> None:
        self.stopped = True

    async def _on_turn(self, event: TurnFinished) -> None:
        self.events.append(event)


class FailsSetup(Recording):
    name = "fails_setup"

    async def setup(self, ctx: PluginContext) -> None:
        await super().setup(ctx)
        raise RuntimeError


class HangsSetup(Recording):
    name = "hangs_setup"

    async def setup(self, ctx: PluginContext) -> None:
        await asyncio.Event().wait()


class FailsShutdown(Recording):
    name = "fails_shutdown"

    async def shutdown(self) -> None:
        raise RuntimeError


class WrongName(Recording):
    name = "other"


class NotAPlugin:
    pass


def _cfg(*enabled: str, settings: Mapping[str, dict[str, object]] | None = None) -> PluginsConfig:
    return PluginsConfig(
        enabled=enabled,
        setup_timeout_s=0.05,
        shutdown_timeout_s=0.05,
        settings=dict(settings or {}),
    )


def _point(name: str, target: str) -> EntryPoint:
    return EntryPoint(name, f"{MODULE}:{target}", ENTRY_POINT_GROUP)


def _found(*points: EntryPoint) -> "_Discover":
    return _Discover(points)


class _Discover:
    def __init__(self, points: Iterable[EntryPoint]) -> None:
        self.points = tuple(points)
        self.calls = 0

    def __call__(self) -> Iterable[EntryPoint]:
        self.calls += 1
        return self.points


@pytest.fixture(autouse=True)
def _clean_instances() -> None:
    Recording.instances.clear()


async def _settle() -> None:
    for _ in range(5):
        await asyncio.sleep(0)


async def test_enabled_plugin_reacts_to_event_and_stops() -> None:
    bus = EventBus()
    discover = _found(_point("recording", "Recording"))
    async with running_plugins(_cfg("recording"), bus, discover):
        await bus.publish(EVENT)
        await _settle()
    plugin = Recording.instances[0]
    assert plugin.events == [EVENT]
    assert plugin.stopped


async def test_disabled_plugin_is_not_imported() -> None:
    bus = EventBus()
    broken_import = EntryPoint("other", "no_such_module_at_all:Plugin", ENTRY_POINT_GROUP)
    discover = _found(_point("recording", "Recording"), broken_import)
    async with running_plugins(_cfg("recording"), bus, discover):
        pass
    assert len(Recording.instances) == 1


async def test_nothing_enabled_costs_nothing() -> None:
    bus = EventBus()
    discover = _found(_point("recording", "Recording"))
    tasks_before = len(asyncio.all_tasks())
    async with running_plugins(_cfg(), bus, discover):
        assert len(asyncio.all_tasks()) == tasks_before
    assert discover.calls == 0
    assert Recording.instances == []


@pytest.mark.parametrize(
    ("name", "target"),
    [
        ("fails_setup", "FailsSetup"),
        ("hangs_setup", "HangsSetup"),
        ("other", "WrongName"),
        ("not_a_plugin", "NotAPlugin"),
        ("no_attr", "NoSuchClass"),
    ],
)
async def test_broken_plugin_does_not_affect_others(name: str, target: str) -> None:
    bus = EventBus()
    points = _found(_point(name, target), _point("recording", "Recording"))
    async with running_plugins(_cfg(name, "recording"), bus, points):
        await bus.publish(EVENT)
        await _settle()
    working = next(p for p in Recording.instances if type(p) is Recording)
    assert working.events == [EVENT]


async def test_failed_setup_gets_no_events() -> None:
    bus = EventBus()
    async with running_plugins(
        _cfg("fails_setup"), bus, _found(_point("fails_setup", "FailsSetup"))
    ):
        await bus.publish(EVENT)
        await _settle()
    assert Recording.instances[0].events == []


async def test_missing_package_is_only_a_warning() -> None:
    async with running_plugins(_cfg("gone"), EventBus(), _found()):
        pass


async def test_failed_shutdown_does_not_stop_others() -> None:
    bus = EventBus()
    points = _found(_point("recording", "Recording"), _point("fails_shutdown", "FailsShutdown"))
    async with running_plugins(_cfg("recording", "fails_shutdown"), bus, points):
        pass
    assert next(p for p in Recording.instances if type(p) is Recording).stopped


async def test_example_plugin_works_through_entry_point(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Настоящий плагин-пример: тот же путь, что после `uv pip install -e plugins/example`.
    root = Path(__file__).parents[3]
    monkeypatch.syspath_prepend(root / "plugins" / "example" / "src")
    bus = EventBus()
    point = EntryPoint("example", "vtuber_example:ExamplePlugin", ENTRY_POINT_GROUP)
    cfg = _cfg("example", settings={"example": {"label": "тест"}})
    stream = io.StringIO()
    with logging_to(LoggingConfig(level="INFO", file=Path("unused")), stream):
        async with running_plugins(cfg, bus, _found(point)):
            await bus.publish(EVENT)
            await _settle()
    logged = {entry["event"]: entry for entry in map(json.loads, stream.getvalue().splitlines())}
    assert logged["example.turn"]["label"] == "тест"
    assert logged["example.turn"]["module"] == "plugin.example"
    assert logged["example.total"]["turns"] == 1
