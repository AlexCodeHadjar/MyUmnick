"""Реестр навыков и гейты (Этап 23, ADR-0043)."""

from collections.abc import AsyncGenerator, Mapping

import pytest

from vtuber.application.memory import TurnHints
from vtuber.application.skills import EnabledCommands, SkillRegistry, gated_hints, gated_stream
from vtuber.domain import IncomingMessage, SkillInfo, plugin_skill


class Choices:
    def __init__(self, saved: dict[str, bool] | None = None) -> None:
        self.saved = dict(saved or {})
        self.writes = 0

    async def load(self) -> dict[str, bool]:
        return dict(self.saved)

    async def save(self, choices: Mapping[str, bool]) -> None:
        self.saved = dict(choices)
        self.writes += 1


TIMER = SkillInfo(id="tools.timer", plugin="tools", title="Таймер")


async def test_loaded_skill_is_on_until_user_turns_it_off() -> None:
    port = Choices()
    registry = await SkillRegistry.open(port)
    registry.add([TIMER])

    assert registry.enabled("tools.timer")
    await registry.set("tools.timer", enabled=False)

    assert not registry.enabled("tools.timer")
    assert port.saved == {"tools.timer": False}
    assert not (await SkillRegistry.open(port)).enabled("tools.timer")


async def test_unknown_skill_is_an_error() -> None:
    registry = await SkillRegistry.open(Choices())
    with pytest.raises(ValueError, match="нет"):
        await registry.set("nope", enabled=True)


async def test_offered_plugin_is_off_and_loads_when_turned_on() -> None:
    port = Choices()
    registry = await SkillRegistry.open(port)
    registry.add([TIMER])
    registry.offer([plugin_skill("web_search"), plugin_skill("tools.timer")])
    loaded: list[str] = []

    async def load(name: str) -> tuple[SkillInfo, ...] | None:
        loaded.append(name)
        return (SkillInfo(id="web_search.search", plugin=name, title="Поиск", network=True),)

    registry.load_plugin = load
    assert not registry.enabled("web_search")
    timer = next(state for state in registry.states() if state.info.id == "tools.timer")
    assert timer.loaded  # уже известный навык не перезаписан предложением

    await registry.set("web_search", enabled=True)

    assert loaded == ["web_search"]
    assert registry.enabled("web_search.search")
    assert [state.info.id for state in registry.states()] == ["tools.timer", "web_search.search"]
    assert registry.wanted_plugins() == ("web_search",)


async def test_plugin_that_fails_to_start_reports_and_stays_off() -> None:
    registry = await SkillRegistry.open(Choices())
    registry.offer([plugin_skill("broken")])

    async def load(_: str) -> tuple[SkillInfo, ...] | None:
        return None

    registry.load_plugin = load
    with pytest.raises(ValueError, match="не запустился"):
        await registry.set("broken", enabled=True)
    assert not registry.enabled("broken")


async def test_stats_count_uses_and_timeouts() -> None:
    registry = await SkillRegistry.open(Choices())
    registry.add([TIMER])
    registry.record("tools.timer", 10.0)
    registry.record("tools.timer", 30.0)
    registry.record("tools.timer", None)

    stats = registry.states()[0].stats
    assert (stats.uses, stats.average_ms, stats.timeouts) == (2, 20.0, 1)


async def test_core_skills_come_first() -> None:
    registry = await SkillRegistry.open(Choices())
    registry.add([TIMER, SkillInfo(id="core.memory", plugin="core", title="Память")])
    assert [state.info.id for state in registry.states()] == ["core.memory", "tools.timer"]


async def test_gates_follow_the_registry_on_every_call() -> None:
    registry = await SkillRegistry.open(Choices({"tools.timer": False}))
    registry.add([TIMER, SkillInfo(id="core.memory", plugin="core", title="Память")])

    async def stop() -> None:
        return None

    commands = EnabledCommands({"стоп": stop, "пауза": stop}, {"стоп": "tools.timer"}, registry)
    assert "стоп" not in commands
    assert list(commands) == ["пауза"]

    async def recall(_: str) -> TurnHints:
        return TurnHints(context=("факт",))

    hints = gated_hints(recall, "core.memory", registry)
    assert (await hints("x")).context == ("факт",)
    await registry.set("core.memory", enabled=False)
    assert (await hints("x")).context == ()


async def test_stream_of_disabled_skill_is_read_but_dropped() -> None:
    registry = await SkillRegistry.open(Choices({"tools.timer": False}))
    registry.add([TIMER])

    async def fired() -> AsyncGenerator[IncomingMessage]:
        yield IncomingMessage("timer", "Таймер", "раз", is_viewer=False)
        await registry.set("tools.timer", enabled=True)
        yield IncomingMessage("timer", "Таймер", "два", is_viewer=False)

    got = [message.text async for message in gated_stream(fired, "tools.timer", registry)()]
    assert got == ["два"]
