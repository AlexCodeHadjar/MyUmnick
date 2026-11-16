"""Мост панели «Навыки» (Этап 23, ADR-0043)."""

from collections.abc import Mapping

from vtuber.application.skills import SkillRegistry
from vtuber.domain import SkillInfo, plugin_skill
from vtuber.gateway import SkillsBridge
from vtuber.gateway.protocol import OutboundMessage
from vtuber.gateway.protocol_skills import SkillsAction, SkillsActionData, SkillsState


class _Choices:
    async def load(self) -> dict[str, bool]:
        return {}

    async def save(self, choices: Mapping[str, bool]) -> None:
        pass


async def _bridge() -> tuple[SkillsBridge, list[OutboundMessage]]:
    registry = await SkillRegistry.open(_Choices())
    registry.add([SkillInfo(id="tools.timer", plugin="tools", title="Таймер", examples=("x",))])
    sent: list[OutboundMessage] = []

    async def send(message: OutboundMessage) -> None:
        sent.append(message)

    async def discover() -> tuple[SkillInfo, ...]:
        return (plugin_skill("web_search", summary="Поиск"),)

    return SkillsBridge(registry, discover, send), sent


def _action(**data: object) -> SkillsAction:
    return SkillsAction.model_validate({"v": 1, "type": "skills.action", "data": data})


async def test_list_offers_installed_plugins() -> None:
    bridge, sent = await _bridge()
    await bridge.handle(_action(action="list"))

    state = sent[-1]
    assert isinstance(state, SkillsState)
    skills = {skill.id: skill for skill in state.data.skills}
    assert skills["tools.timer"].enabled
    assert skills["tools.timer"].examples == ["x"]
    assert not skills["web_search"].loaded
    assert not skills["web_search"].enabled


async def test_toggle_and_problems_are_reported() -> None:
    bridge, sent = await _bridge()
    await bridge.handle(_action(action="set", id="tools.timer", enabled=False))
    state = sent[-1]
    assert isinstance(state, SkillsState)
    assert not state.data.skills[0].enabled
    assert state.data.problem is None

    await bridge.handle(_action(action="set", id="nope", enabled=True))
    assert isinstance(sent[-1], SkillsState)
    assert sent[-1].data.problem is not None

    await bridge.handle(
        SkillsAction(v=1, type="skills.action", data=SkillsActionData(action="set"))
    )
    assert isinstance(sent[-1], SkillsState)
    assert sent[-1].data.problem is not None
