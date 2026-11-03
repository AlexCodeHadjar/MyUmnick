import asyncio
from collections.abc import AsyncGenerator
from contextlib import aclosing

import pytest
from websockets.asyncio.server import ServerConnection, serve

from vtuber.domain import IncomingMessage
from vtuber.kernel import EventBus, PluginContext
from vtuber_stream_chat import (
    ChatFilterConfig,
    ChatQueue,
    ChatQueueConfig,
    RateLimiter,
    StreamChatPlugin,
    TwitchChat,
    parse_privmsg,
    passes_filter,
)


def _msg(text: str, author: str = "зритель") -> IncomingMessage:
    return IncomingMessage("fake", author, text)


class _Time:
    """Часы, которые двигает `sleep`: лимит частоты проверяется без реального ожидания."""

    def __init__(self) -> None:
        self.now = 100.0
        self.slept: list[float] = []

    def clock(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


class _FakeSource:
    def __init__(self, *messages: IncomingMessage) -> None:
        self._messages = messages

    async def messages(self) -> AsyncGenerator[IncomingMessage]:
        for message in self._messages:
            yield message
        await asyncio.Event().wait()


@pytest.mark.parametrize(
    "text",
    ["!команда", "смотри https://spam.example", "заходи на site.ru", "a", "x" * 301, "тут плохо"],
)
def test_filter_rejects(text: str) -> None:
    cfg = ChatFilterConfig(blocked_words=("ПЛОХО",))
    assert not passes_filter(_msg(text), cfg)


def test_filter_accepts_plain_message_and_rejects_ignored_author() -> None:
    cfg = ChatFilterConfig(ignored_authors=("NightBot",))
    assert passes_filter(_msg("Привет, как дела"), cfg)
    assert not passes_filter(_msg("Привет, как дела", "nightbot"), cfg)


def _queue(time: _Time, **kwargs: object) -> ChatQueue:
    cfg = ChatQueueConfig.model_validate({"mention_names": ("мика",), **kwargs})
    return ChatQueue(cfg, ChatFilterConfig(), time.clock)


def test_mention_beats_question_beats_newest() -> None:
    queue = _queue(_Time())
    for text in ("просто так", "кто ты?", "Мика, привет", "ещё просто так"):
        queue.add(_msg(text))
    picked = [queue.pick(), queue.pick(), queue.pick(), queue.pick(), queue.pick()]
    assert [m.text if m else None for m in picked] == [
        "Мика, привет",
        "кто ты?",
        "ещё просто так",
        "просто так",
        None,
    ]


def test_overflow_loses_oldest_and_stale_are_not_voiced() -> None:
    time = _Time()
    queue = _queue(time, max_size=2, max_age_s=10.0)
    for text in ("один", "два", "три"):
        queue.add(_msg(text))
    assert queue.pick() == _msg("три")
    time.now += 11
    assert queue.pick() is None


def test_repeat_of_waiting_message_is_dropped() -> None:
    queue = _queue(_Time())
    queue.add(_msg("Привет"))
    queue.add(_msg("привет ", "другой"))
    assert queue.pick() == _msg("Привет")
    assert queue.pick() is None


async def test_rate_limit_holds_between_answers() -> None:
    time = _Time()
    limiter = RateLimiter(20.0, time.clock, time.sleep)
    await limiter.wait()
    limiter.mark()
    time.now += 5
    await limiter.wait()
    assert time.slept == [15.0]


async def test_plugin_yields_selected_messages_at_most_at_limit() -> None:
    bus = EventBus()
    ctx = PluginContext(
        "stream_chat",
        bus,
        {"channel": "c", "min_interval_s": 0.05, "queue": {"mention_names": ["мика"]}},
    )
    plugin = StreamChatPlugin(_FakeSource(_msg("!бот"), _msg("обычное"), _msg("Мика, ты тут?")))
    await plugin.setup(ctx)
    await asyncio.sleep(0)
    loop = asyncio.get_running_loop()
    async with aclosing(ctx.sources[0]()) as stream:
        first = await anext(stream)
        started = loop.time()
        second = await anext(stream)
        elapsed = loop.time() - started
    await plugin.shutdown()
    assert (first.text, second.text) == ("Мика, ты тут?", "обычное")
    assert elapsed >= 0.04


def test_parse_privmsg() -> None:
    line = ":viewer!viewer@viewer.tmi.twitch.tv PRIVMSG #chan :Привет :)\r\n"
    assert parse_privmsg(line) == IncomingMessage("twitch", "viewer", "Привет :)")
    assert parse_privmsg(":tmi.twitch.tv 001 justinfan1 :Welcome") is None


async def test_twitch_joins_anonymously_answers_ping_and_reconnects() -> None:
    received: list[str] = []
    connections = 0

    async def handler(ws: ServerConnection) -> None:
        nonlocal connections
        connections += 1
        received.extend([str(await ws.recv()) for _ in range(3)])
        await ws.send("PING :tmi.twitch.tv")
        received.append(str(await ws.recv()))
        await ws.send(f":a!a@a PRIVMSG #chan :сообщение {connections}")

    async with serve(handler, "127.0.0.1", 0) as server:
        port = next(iter(server.sockets)).getsockname()[1]
        chat = TwitchChat("#Chan", f"ws://127.0.0.1:{port}", reconnect_s=0.01)
        async with aclosing(chat.messages()) as messages:
            first = await asyncio.wait_for(anext(messages), 5)
            second = await asyncio.wait_for(anext(messages), 5)
    assert (first.text, second.text) == ("сообщение 1", "сообщение 2")
    assert received[0] == "PASS SCHMOOPIIE"
    assert received[1].startswith("NICK justinfan")
    assert received[2:4] == ["JOIN #chan", "PONG :tmi.twitch.tv"]
