"""Обращение по имени и незаконченные фразы (S-14.1, S-14.2)."""

import array
import asyncio
from dataclasses import dataclass, field

import pytest

from tests.fakes import FakeSTT, FakeVad
from vtuber.application.voice import (
    AddressedEvents,
    AddressingConfig,
    SegmenterConfig,
    VoiceConfig,
    VoiceListener,
    addressed,
    looks_unfinished,
    name_pattern,
    without_call,
)
from vtuber.domain import AudioChunk, AudioFormat

RATE = AudioFormat(16_000)
SEGMENTS = SegmenterConfig(
    threshold=0.5,
    start_ms=96,
    end_silence_ms=320,
    barge_in_ms=300,
    pre_roll_ms=64,
    max_phrase_s=20.0,
)
HOLD_MS = 150


@dataclass(slots=True)
class _Events:
    log: list[str] = field(default_factory=list)

    async def barge_in(self) -> None:
        self.log.append("перебить")

    async def hypothesis(self, text: str) -> None:
        self.log.append(f"гипотеза: {text}")

    async def final(self, text: str, ended_ns: int) -> None:
        del ended_ns
        self.log.append(f"фраза: {text}")


@pytest.mark.parametrize(
    ("text", "asked"),
    [
        ("Мика, как дела?", "как дела"),
        ("Эй, Мика, ты тут?", "ты тут"),
        ("слушай, мика, что нового", "что нового"),
        ("Как дела, Мика?", "Как дела"),
        ("Умник, какая сегодня погода в Москве?", "какая сегодня погода в Москве"),
    ],
)
async def test_address_by_name_starts_a_turn_without_the_name(text: str, asked: str) -> None:
    events = _Events()
    await AddressedEvents(events, ("мика", "умник")).final(text, 0)
    assert events.log == ["перебить", f"фраза: {asked}"]


async def test_name_alone_waits_for_the_request() -> None:
    now = [100.0]
    events = _Events()
    bridge = AddressedEvents(events, ("умник",), follow_up_s=8.0, clock=lambda: now[0])

    await bridge.final("Умник!", 0)
    assert events.log == ["перебить"]
    now[0] += 3
    await bridge.final("Какая погода в Казани?", 0)
    assert events.log[-1] == "фраза: Какая погода в Казани?"

    await bridge.final("Умник.", 0)
    now[0] += 9
    await bridge.final("Это я не тебе", 0)
    assert events.log[-1] != "фраза: Это я не тебе"


def test_speaker_label_stays_with_the_request() -> None:
    pattern = name_pattern(("умник",))
    assert without_call("Собеседник 2: Умник, привет", pattern) == "Собеседник 2: привет"
    assert without_call("Умник", pattern) == ""


@pytest.mark.parametrize(
    "text",
    ["Как дела?", "Передай мне соль", "Микаэль вчера звонил", "Я купил микроволновку"],
)
async def test_room_talk_does_nothing(text: str) -> None:
    events = _Events()
    bridge = AddressedEvents(events, ("мика",))
    await bridge.barge_in()
    await bridge.hypothesis(text)
    await bridge.final(text, 0)
    assert events.log == []


async def test_barge_in_comes_once_when_the_name_is_heard() -> None:
    events = _Events()
    bridge = AddressedEvents(events, ("мика",))
    await bridge.hypothesis("Мика, подожди")
    await bridge.hypothesis("Мика, подожди секунду")
    await bridge.final("Мика, подожди секунду.", 0)
    assert events.log.count("перебить") == 1
    await bridge.final("Мика, ещё раз", 0)
    assert events.log.count("перебить") == 2


def test_always_mode_has_no_wrapper() -> None:
    events = _Events()
    always = AddressingConfig(mode="always", names=("мика",), follow_up_s=8)
    assert addressed(always, events) is events
    by_name = AddressingConfig(mode="by_name", names=("мика",), follow_up_s=8)
    assert isinstance(addressed(by_name, events), AddressedEvents)


@pytest.mark.parametrize(
    "text",
    ["Я хотел", "Я хотела...", "Ну и потом мы пошли в", "Это потому что", "Подожди, я думаю…"],
)
def test_broken_off_phrases_look_unfinished(text: str) -> None:
    assert looks_unfinished(text)


@pytest.mark.parametrize(
    "text",
    [
        "Как дела?",
        "Я хотел спросить про погоду.",
        "Что?",
        "И что!",
        "Спасибо",
        "",
        "Да, конечно.",
        "Да.",
        "Ну",
        "Вот так.",
        "А это",
    ],
)
def test_finished_phrases_go_straight_away(text: str) -> None:
    assert not looks_unfinished(text)


def _audio(seconds: float, *, loud: bool) -> AudioChunk:
    count = round(seconds * RATE.sample_rate)
    return AudioChunk(RATE, array.array("h", [8000 if loud else 0] * count).tobytes())


async def _settle() -> None:
    for _ in range(2000):
        await asyncio.sleep(0)


class _Hearing:
    """Слушатель на фейках; между фразами подменяется текст распознавания."""

    def __init__(self) -> None:
        self.stt = FakeSTT("Я хотел")
        self.events = _Events()
        cfg = VoiceConfig(
            interim_ms=60_000, min_phrase_ms=200, segmenter=SEGMENTS, unfinished_hold_ms=HOLD_MS
        )
        self.listener = VoiceListener(FakeVad(), self.stt, self.events, cfg)
        self.loop = asyncio.create_task(self.listener.run())

    async def say(self, seconds: float = 0.6) -> None:
        self.listener.feed(_audio(seconds, loud=True))
        self.listener.feed(_audio(0.5, loud=False))
        await _settle()

    def finals(self) -> list[str]:
        return [line for line in self.events.log if line.startswith("фраза")]

    async def stop(self) -> None:
        self.loop.cancel()
        await asyncio.wait([self.loop])


async def test_unfinished_phrase_joins_the_continuation() -> None:
    hearing = _Hearing()
    await hearing.say()
    assert hearing.finals() == [], "ответ не должен начаться на паузе посреди мысли"
    hearing.stt.text = "спросить про погоду."
    await hearing.say()
    assert hearing.finals() == ["фраза: Я хотел спросить про погоду."]
    await asyncio.sleep(HOLD_MS * 2 / 1000)
    assert len(hearing.finals()) == 1
    await hearing.stop()


async def test_unfinished_phrase_goes_after_the_hold_if_nothing_follows() -> None:
    hearing = _Hearing()
    await hearing.say()
    await asyncio.sleep(HOLD_MS * 2 / 1000)
    assert hearing.finals() == ["фраза: Я хотел"]
    await hearing.stop()


async def test_failed_continuation_does_not_lose_the_phrase() -> None:
    hearing = _Hearing()
    await hearing.say()
    hearing.stt.available = False
    await hearing.say()
    assert hearing.finals() == ["фраза: Я хотел"]
    await hearing.stop()


async def test_hold_off_keeps_the_old_behaviour() -> None:
    stt, events = FakeSTT("Я хотел"), _Events()
    cfg = VoiceConfig(interim_ms=60_000, min_phrase_ms=200, segmenter=SEGMENTS)
    listener = VoiceListener(FakeVad(), stt, events, cfg)
    loop = asyncio.create_task(listener.run())
    listener.feed(_audio(0.6, loud=True))
    listener.feed(_audio(0.5, loud=False))
    await _settle()
    assert "фраза: Я хотел" in events.log
    loop.cancel()
    await asyncio.wait([loop])
