import asyncio
from contextlib import aclosing
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vtuber.application.tools import ToolContext
from vtuber.kernel import EventBus, PluginContext
from vtuber_tools import AddNote, AskTime, ListNotes, SetTimer, ToolsPlugin, detect_intent


@pytest.mark.parametrize(
    ("text", "intent"),
    [
        ("Который час?", AskTime()),
        ("Скажи, какое сегодня число", AskTime()),
        ("Поставь таймер на 5 минут", SetTimer(300, "")),
        ("таймер на тридцать секунд", SetTimer(30, "")),
        ("Напомни через час позвонить маме", SetTimer(3600, "позвонить маме")),
        ("Поставь таймер на полчаса", SetTimer(1800, "")),
        ("Запиши в заметки купить молоко", AddNote("купить молоко")),
        ("Добавь заметку: позвонить маме", AddNote("позвонить маме")),
        ("Какие у меня заметки?", ListNotes()),
    ],
)
def test_detects_requests(text: str, intent: object) -> None:
    assert detect_intent(text) == intent


@pytest.mark.parametrize(
    "text",
    [
        "Привет, как дела?",
        "Расскажи про время в романах",
        "Я вчера поставил чайник на плиту",
        "Напомни, о чём мы говорили",
        "Мне нравится записывать музыку",
    ],
)
def test_ordinary_replies_are_not_tool_requests(text: str) -> None:
    assert detect_intent(text) is None


async def _plugin(tmp_path: Path) -> ToolsPlugin:
    plugin = ToolsPlugin(now=lambda: datetime(2026, 11, 3, 14, 5, tzinfo=UTC))
    settings = {"notes_file": str(tmp_path / "notes.txt"), "max_notes_read": 2}
    await plugin.setup(PluginContext("tools", EventBus(), settings))
    return plugin


async def test_time_goes_to_context_in_russian(tmp_path: Path) -> None:
    plugin = await _plugin(tmp_path)
    assert await plugin.context("Который час?") == "Сейчас 14:05, вторник, 3 ноября 2026."
    assert await plugin.context("Привет") is None


async def test_notes_are_kept_in_file_and_latest_are_read(tmp_path: Path) -> None:
    plugin = await _plugin(tmp_path)
    assert await plugin.context("Какие у меня заметки?") == "Заметок пока нет."
    for text in ("раз", "два", "три"):
        await plugin.context(f"Запиши в заметки {text}")
    assert await plugin.context("Какие у меня заметки?") == "Заметки: два; три."


async def test_timer_rings_through_source(tmp_path: Path) -> None:
    plugin = await _plugin(tmp_path)
    # Секунды — наименьшая единица: таймер этого теста звучит на самом деле.
    answer = await plugin.context("Поставь таймер на 1 секунду")
    assert answer is not None
    assert "поставлен" in answer
    async with aclosing(plugin.fired()) as fired:
        message = await asyncio.wait_for(anext(fired), 3)
    assert message.text == "сработал таймер на 1 сек"
    await plugin.shutdown()


async def test_context_collects_answers_and_survives_slow_and_broken_tools() -> None:
    async def fast(_: str) -> str | None:
        return "Сейчас 14:05."

    async def silent(_: str) -> str | None:
        return None

    async def slow(_: str) -> str | None:
        await asyncio.Event().wait()
        return "поздно"

    async def broken(_: str) -> str | None:
        raise RuntimeError

    hints = await ToolContext((slow, fast, broken, silent), timeout_s=0.02).hints("который час")
    assert hints.context == ("Сейчас 14:05.",)
