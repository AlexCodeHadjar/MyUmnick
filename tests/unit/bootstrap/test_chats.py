"""Переключатель чатов (Этап 21): память и история меняются на ходу, без старых подписчиков."""

import asyncio
from pathlib import Path

from tests.fakes import FakeLLM
from tests.fakes.conversation import TEST_PERSONA
from vtuber.application.conversation import ConversationService
from vtuber.application.memory import ShortTermMemory
from vtuber.application.pipeline import ReplyPipeline
from vtuber.application.prompting import ContextBudget, ContextConfig, PromptBuilder
from vtuber.bootstrap import load_app_config
from vtuber.bootstrap.chats import ChatRelay, ChatSwitcher, chat_profile
from vtuber.bootstrap.container import Conversation, Core
from vtuber.domain import MAIN_CHAT, Turn, TurnId, TurnRemembered
from vtuber.kernel import EventBus, Telemetry
from vtuber.ports import GenerationParams

ROOT = Path(__file__).resolve().parents[3]


def test_main_chat_keeps_old_profile_others_get_their_own() -> None:
    assert chat_profile(MAIN_CHAT, "") == ""
    assert chat_profile(MAIN_CHAT, "anya") == "anya"
    assert chat_profile("ab12", "") == "chat-ab12"


async def test_relay_cuts_off_previous_chat() -> None:
    bus = EventBus()
    relay = ChatRelay(bus)
    seen: list[str] = []

    async def first(_: TurnRemembered) -> None:
        seen.append("first")

    async def second(_: TurnRemembered) -> None:
        seen.append("second")

    relay.chat_bus.subscribe(TurnRemembered, first)
    relay.renew().subscribe(TurnRemembered, second)
    await bus.publish(TurnRemembered(Turn(TurnId(1), "a", "b"), ()))

    assert seen == ["second"]


async def test_switch_clears_history_and_reports_new_chat() -> None:
    cfg = load_app_config(ROOT, {"VTUBER_MEMORY__ENABLED": "false"})
    bus = EventBus()
    conversation = _conversation(bus)
    conversation.history.append(Turn(TurnId(1), "Привет", "Привет!"))
    core = Core(bus, Telemetry(bus))
    switcher = ChatSwitcher(cfg, lambda _: cfg.memory, None, (conversation, core))
    opened: list[int] = []

    async def on_open(controls: object, chat_core: Core) -> None:
        opened.append(len(conversation.history.turns))
        assert controls is None
        assert chat_core.bus is not bus

    switcher.on_open = on_open
    owner = asyncio.create_task(switcher.run(MAIN_CHAT))
    await asyncio.sleep(0)
    await switcher.switch("ab12")
    owner.cancel()

    assert opened == [1, 0]


def _conversation(bus: EventBus) -> Conversation:
    budget = ContextBudget(
        ContextConfig(
            max_history_tokens=10_000, trim_ratio=0.5, chars_per_token=3, message_overhead_tokens=4
        )
    )
    history = ShortTermMemory(budget)
    prompts = PromptBuilder(TEST_PERSONA)
    params = GenerationParams(max_tokens=8, temperature=0.0)
    pipeline = ReplyPipeline(FakeLLM("ok"), params, Telemetry(bus))
    return Conversation(ConversationService(pipeline, prompts, history, bus), prompts, history)
