"""Мост чатов (Этап 21): действия UI → каталог, открытие чата → смена памяти, список → UI."""

from datetime import UTC, datetime

from vtuber.application.chats import ChatDirectory
from vtuber.domain import MAIN_CHAT, ChatInfo, ChatList
from vtuber.gateway import ChatsBridge
from vtuber.gateway.protocol import OutboundMessage
from vtuber.gateway.protocol_chats import ChatAction, ChatActionData, ChatsState

WHEN = datetime(2026, 11, 10, tzinfo=UTC)


class _Catalog:
    async def load(self) -> ChatList:
        return ChatList((ChatInfo(MAIN_CHAT, "", None, WHEN),), ())

    async def save(self, chats: ChatList) -> None:
        pass

    async def erase(self, chat_id: str) -> None:
        pass


async def _bridge() -> tuple[ChatsBridge, list[OutboundMessage], list[str]]:
    sent: list[OutboundMessage] = []
    switched: list[str] = []

    async def send(message: OutboundMessage) -> None:
        sent.append(message)

    async def switch(chat_id: str) -> None:
        switched.append(chat_id)

    directory = ChatDirectory(_Catalog(), await _Catalog().load(), clock=lambda: WHEN)
    return ChatsBridge(directory, switch, send), sent, switched


def _act(action: str, **fields: str | None) -> ChatAction:
    data = ChatActionData.model_validate({"action": action, **fields})
    return ChatAction(v=1, type="chats.action", data=data)


def _last_state(sent: list[OutboundMessage]) -> ChatsState:
    states = [message for message in sent if isinstance(message, ChatsState)]
    return states[-1]


async def test_create_opens_new_chat_through_switch() -> None:
    bridge, sent, switched = await _bridge()

    await bridge.handle(_act("create"))

    state = _last_state(sent).data
    assert len(state.chats) == 2
    assert state.active != MAIN_CHAT
    assert switched == [state.active]
    assert state.switching is False
    assert any(isinstance(m, ChatsState) and m.data.switching for m in sent)


async def test_opening_the_open_chat_does_not_switch() -> None:
    bridge, _, switched = await _bridge()

    await bridge.handle(_act("open", id=MAIN_CHAT))

    assert switched == []


async def test_category_flow_and_move() -> None:
    bridge, sent, _ = await _bridge()

    await bridge.handle(_act("category_create", name="Игры"))
    category = _last_state(sent).data.categories[0].id
    await bridge.handle(_act("move", id=MAIN_CHAT, category=category))

    assert _last_state(sent).data.chats[0].category == category


async def test_bad_action_is_reported_not_raised() -> None:
    bridge, sent, _ = await _bridge()

    await bridge.handle(_act("delete", id=MAIN_CHAT))
    await bridge.handle(_act("rename", id=MAIN_CHAT))

    problems = [m.data.problem for m in sent if isinstance(m, ChatsState)]
    assert problems[0] is not None
    assert problems[-1] is not None
