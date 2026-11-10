"""Дерево диалога: ветка не меняет исходную, промпт берёт только активную (S-16.1)."""

import asyncio
from collections.abc import AsyncGenerator, Sequence

import pytest

from tests.fakes import FakeClock, FakeLLM, RecordingSink
from tests.fakes.conversation import make_conversation
from vtuber.application.conversation import ConversationService, DialogueTree
from vtuber.domain import Message, Turn, TurnId, TurnRemembered
from vtuber.gateway import BranchBridge, OutboundMessage
from vtuber.gateway.branch_bridge import shown_text
from vtuber.gateway.protocol_branches import (
    BranchCheckpoint,
    BranchCheckpointData,
    BranchGo,
    BranchGoData,
    BranchState,
)
from vtuber.kernel import EventBus, Telemetry
from vtuber.ports import GenerationParams


def _turn(number: int, text: str) -> Turn:
    return Turn(TurnId(number), text, f"ответ на {text}")


def _tree() -> DialogueTree:
    tree = DialogueTree()
    for number, text in enumerate(("а", "б", "в"), start=1):
        tree.add(_turn(number, text))
    return tree


def _texts(turns: Sequence[Turn]) -> list[str]:
    return [turn.user_text for turn in turns]


def test_new_turn_after_going_back_forks_and_keeps_the_original() -> None:
    tree = _tree()
    tree.go(TurnId(1))
    tree.add(_turn(4, "г"))
    assert _texts(tree.path()) == ["а", "г"]
    assert _texts(tree.go(TurnId(3))) == ["а", "б", "в"]


def test_branches_are_listed_and_only_one_is_active() -> None:
    tree = _tree()
    tree.go(TurnId(1))
    tree.add(_turn(4, "г"))
    branches = {branch.title: branch for branch in tree.branches()}
    assert set(branches) == {"в", "г"}
    assert branches["г"].active
    assert not branches["в"].active
    assert (branches["в"].length, branches["г"].length) == (3, 2)


def test_going_back_without_new_turn_keeps_the_branch_active() -> None:
    tree = _tree()
    tree.go(TurnId(2))
    (branch,) = tree.branches()
    assert branch.leaf == TurnId(3)
    assert branch.active


def test_checkpoint_returns_to_its_place() -> None:
    tree = _tree()
    tree.go(TurnId(2))
    tree.checkpoint(" до развилки ")
    tree.add(_turn(4, "г"))
    (point,) = tree.checkpoints()
    assert point.name == "до развилки"
    assert _texts(tree.go(point.turn)) == ["а", "б"]


@pytest.mark.parametrize("name", ["", "   "])
def test_checkpoint_needs_a_name(name: str) -> None:
    with pytest.raises(ValueError, match="имя"):
        _tree().checkpoint(name)


def test_checkpoint_needs_a_turn() -> None:
    with pytest.raises(ValueError, match="реплик"):
        DialogueTree().checkpoint("имя")


def test_unknown_turn_is_refused() -> None:
    tree = _tree()
    with pytest.raises(ValueError, match="нет такой"):
        tree.go(TurnId(99))
    assert _texts(tree.path()) == ["а", "б", "в"]


def test_restored_turns_get_their_own_numbers() -> None:
    tree = DialogueTree()
    tree.seed([Turn(TurnId(0), "старая", "о"), Turn(TurnId(0), "старая 2", "о")])
    assert _texts(tree.path()) == ["старая", "старая 2"]
    assert {turn.id for turn in tree.path()} == {TurnId(-1), TurnId(-2)}


async def test_private_turns_are_not_kept() -> None:
    bus = EventBus()
    tree = DialogueTree()
    tree.follow(bus)
    await bus.publish(TurnRemembered(Turn(TurnId(1), "", "", is_private=True), ()))
    assert tree.path() == ()


def test_tags_are_not_shown_in_chat() -> None:
    assert shown_text("<happy>Привет!") == "Привет!"


class _Setup:
    def __init__(self, llm: FakeLLM) -> None:
        self.bus = EventBus()
        self.service: ConversationService = make_conversation(
            llm, self.bus, Telemetry(self.bus, FakeClock())
        )
        self.tree = DialogueTree()
        self.tree.follow(self.bus)
        self.sent: list[OutboundMessage] = []

        async def send(message: OutboundMessage) -> None:
            self.sent.append(message)

        self.bridge = BranchBridge(self.service, self.tree, send)

    async def say(self, text: str) -> None:
        await self.service.handle(text, RecordingSink())
        await self.service.wait_idle()

    async def go(self, ref: str) -> None:
        message = BranchGo(v=1, type="branch.go", data=BranchGoData(turn=ref))
        await self.bridge.handle(message)
        await self.service.wait_idle()

    def last(self) -> BranchState:
        message = self.sent[-1]
        assert isinstance(message, BranchState)
        return message


async def test_prompt_takes_only_the_active_branch() -> None:
    llm = FakeLLM("<happy>Ответ")
    world = _Setup(llm)
    await world.say("первая")
    await world.say("тупик")
    await world.go("t-000001")
    await world.say("другая")

    sent = str(llm.calls[-1][0])
    assert "первая" in sent
    assert "тупик" not in sent
    assert "другая" in sent

    state = world.last().data
    assert [m.text for m in state.messages] == ["первая", "Ответ"]
    assert state.messages[1].turn == "t-000001"
    assert state.problem is None


async def test_going_back_returns_old_branch_to_the_prompt() -> None:
    llm = FakeLLM("Ответ")
    world = _Setup(llm)
    await world.say("первая")
    await world.say("старая ветка")
    await world.go("t-000001")
    await world.say("новая ветка")
    await world.go("t-000002")
    await world.say("дальше")
    sent = str(llm.calls[-1][0])
    assert "старая ветка" in sent
    assert "новая ветка" not in sent


class _SlowLLM:
    """Поток, который останавливается по отмене: посреди ответа можно перейти в другую ветку."""

    def __init__(self) -> None:
        self.started = asyncio.Event()

    async def stream(
        self, messages: Sequence[Message], params: GenerationParams
    ) -> AsyncGenerator[str]:
        yield "Начало"
        self.started.set()
        await asyncio.Event().wait()

    async def prefill(self, messages: Sequence[Message]) -> None:
        await asyncio.sleep(0)


async def test_going_back_during_a_reply_keeps_it_in_the_old_branch() -> None:
    llm = _SlowLLM()
    bus = EventBus()
    service = make_conversation(llm, bus, Telemetry(bus, FakeClock()))
    tree = DialogueTree()
    tree.follow(bus)
    tree.add(_turn(-1, "первая"))
    sent: list[OutboundMessage] = []

    async def send(message: OutboundMessage) -> None:
        sent.append(message)

    bridge = BranchBridge(service, tree, send)
    await service.handle("вторая", RecordingSink())
    await asyncio.wait_for(llm.started.wait(), 1)

    message = BranchGo(v=1, type="branch.go", data=BranchGoData(turn="t--00001"))
    await bridge.handle(message)

    assert _texts(tree.path()) == ["первая"]
    (branch,) = tree.branches()
    assert branch.title == "вторая"  # прерванный ответ остался в прежней ветке
    await service.wait_idle()


async def test_problem_is_reported_and_checkpoint_listed() -> None:
    world = _Setup(FakeLLM("Ответ"))
    await world.say("первая")
    await world.go("не номер")
    assert world.last().data.problem
    await world.go("t-000099")
    assert world.last().data.problem
    data = BranchCheckpointData(name="точка")
    await world.bridge.handle(BranchCheckpoint(v=1, type="branch.checkpoint", data=data))
    (point,) = world.last().data.checkpoints
    assert (point.name, point.turn) == ("точка", "t-000001")


async def test_nothing_is_sent_for_an_empty_dialogue() -> None:
    world = _Setup(FakeLLM("Ответ"))
    await world.bridge.send_state()
    assert world.sent == []


async def test_empty_chat_state_is_sent_only_when_asked() -> None:
    world = _Setup(FakeLLM("<happy>Ответ"))

    await world.bridge.send_state()
    assert world.sent == []
    await world.bridge.send_state(always=True)

    assert world.last().data.messages == []
