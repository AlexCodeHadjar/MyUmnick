"""Приватный режим и очистка на фейках: что запоминается и что нет (S-17.2)."""

import asyncio
from datetime import UTC, datetime

from tests.fakes import FakeClock, FakeEmbedder, FakeLLM, FakeMemoryStore, RecordingSink
from tests.fakes.conversation import make_conversation
from tests.fakes.fake_vault import FakeVault
from vtuber.application.memory import ChatRecorder, MemoryEraser, ShortTermMemory, TurnHints
from vtuber.application.prompting import ContextBudget, ContextConfig
from vtuber.domain import EmbedKind, Fact, FactSource, Turn, TurnId, TurnRemembered
from vtuber.kernel import EventBus, Telemetry

WHEN = datetime(2026, 11, 3, 14, tzinfo=UTC)


def _history(max_tokens: int = 10_000) -> ShortTermMemory:
    budget = ContextConfig(
        max_history_tokens=max_tokens, trim_ratio=0.5, chars_per_token=3, message_overhead_tokens=4
    )
    return ShortTermMemory(ContextBudget(budget))


def _turn(text: str, *, private: bool = False) -> Turn:
    return Turn(TurnId(1), text, "ответ", is_private=private)


def test_private_turns_are_forgotten_when_mode_ends() -> None:
    history = _history()
    history.append(_turn("обычная"))
    history.append(_turn("секрет", private=True))
    assert "секрет" in str(history.messages)

    history.forget_private()

    assert "секрет" not in str(history.messages)
    assert "обычная" in str(history.messages)


def test_private_turns_never_reach_the_summary() -> None:
    history = _history(max_tokens=30)
    history.append(_turn("секрет", private=True))
    dropped = history.append(_turn("длинная реплика " * 20))
    assert "секрет" not in str(dropped)


def test_clear_forgets_everything() -> None:
    history = _history()
    history.restore([_turn("старая")], "резюме")
    history.clear()
    assert history.messages == ()
    assert history.summary is None
    assert history.tokens == 0


def _service(llm: FakeLLM) -> tuple[object, list[TurnRemembered]]:
    bus = EventBus()
    seen: list[TurnRemembered] = []

    async def on_turn(event: TurnRemembered) -> None:
        seen.append(event)

    bus.subscribe(TurnRemembered, on_turn)
    return make_conversation(llm, bus, Telemetry(bus, FakeClock())), seen


async def test_private_turn_tells_nobody_its_text() -> None:
    service, seen = _service(FakeLLM("тайный ответ"))
    service.set_private(enabled=True)  # type: ignore[attr-defined]
    await service.handle("секрет", RecordingSink())  # type: ignore[attr-defined]
    await service.wait_idle()  # type: ignore[attr-defined]
    assert seen[0].turn.is_private
    assert seen[0].turn.user_text == ""
    assert seen[0].turn.reply_text == ""


async def test_private_turn_gets_memory_but_no_tools() -> None:
    llm = FakeLLM("Ок")
    service, _ = _service(llm)
    tools: list[str] = []

    async def tool(text: str) -> TurnHints:
        tools.append(text)
        return TurnHints(context=("инструмент",))

    async def memory(_: str) -> TurnHints:
        return TurnHints(context=("факт из памяти",))

    service.use_tools(tool)  # type: ignore[attr-defined]
    service.use_memory(memory)  # type: ignore[attr-defined]
    service.set_private(enabled=True)  # type: ignore[attr-defined]
    await service.handle("запиши в заметки секрет", RecordingSink())  # type: ignore[attr-defined]
    await service.wait_idle()  # type: ignore[attr-defined]
    assert tools == []
    assert "факт из памяти" in llm.calls[0][0][-1].text


async def test_turn_finishing_after_mode_ended_is_not_kept() -> None:
    llm = FakeLLM("Ок")
    service, _ = _service(llm)
    service.set_private(enabled=True)  # type: ignore[attr-defined]
    await service.handle("секрет", RecordingSink())  # type: ignore[attr-defined]
    service.set_private(enabled=False)  # type: ignore[attr-defined]
    await service.wait_idle()  # type: ignore[attr-defined]
    await service.handle("дальше", RecordingSink())  # type: ignore[attr-defined]
    await service.wait_idle()  # type: ignore[attr-defined]
    assert "секрет" not in str(llm.calls[-1][0])


async def test_recorder_skips_private_turns() -> None:
    bus = EventBus()
    vault = FakeVault()
    recorder = ChatRecorder(vault)
    recorder.follow(bus)
    running = asyncio.create_task(recorder.run())
    await bus.publish(TurnRemembered(_turn("", private=True), ()))
    await bus.publish(TurnRemembered(_turn("обычная"), ()))
    recorder.stop()
    await asyncio.wait_for(running, 1)
    assert [t.user_text for t in vault.turns] == ["обычная"]


async def test_eraser_quiets_writers_then_removes_notes_index_and_history() -> None:
    vault = FakeVault()
    store = FakeMemoryStore(dimensions=8)
    history = _history()
    history.append(_turn("обычная"))
    saved = await vault.save_fact(Fact("факт", FactSource.USER, 0.5, WHEN))
    vector = (await FakeEmbedder(8).embed(["факт"], EmbedKind.PASSAGE))[0]
    await store.add(saved, vector)
    await vault.save_turn(_turn("обычная"), WHEN)
    order: list[str] = []

    async def quiet() -> None:
        order.append(f"тихо, заметок {len(vault.notes)}")

    await MemoryEraser(vault, store, history, quiet).erase()

    assert order == ["тихо, заметок 1"]
    assert await vault.facts() == []
    assert await vault.recent_turns(5) == []
    assert await store.all_facts() == []
    assert history.messages == ()
