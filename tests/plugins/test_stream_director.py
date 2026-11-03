import asyncio
from collections.abc import AsyncGenerator, Mapping
from contextlib import aclosing

from vtuber.domain import IncomingMessage, Turn, TurnId, TurnRemembered
from vtuber.kernel import EventBus, PluginContext
from vtuber_stream_chat import (
    EVENT_SOURCE,
    ChatFilterConfig,
    ChatQueue,
    ChatQueueConfig,
    RateLimiter,
    parse_twitch_line,
)
from vtuber_stream_director import ObsStage, StreamDirector, StreamDirectorPlugin

TICK_S = 0.02


def _msg(text: str, author: str = "зритель") -> IncomingMessage:
    return IncomingMessage("fake", author, text)


class _Stage:
    def __init__(self) -> None:
        self.log: list[str] = []

    async def live(self) -> None:
        self.log.append("live")

    async def paused(self) -> None:
        self.log.append("paused")

    async def question(self, message: IncomingMessage) -> None:
        self.log.append(f"question {message.text}")


def _director(*, interval_s: float = 0.0, hold_s: float = 0.0) -> tuple[StreamDirector, _Stage]:
    stage = _Stage()
    queue = ChatQueue(ChatQueueConfig(mention_names=("мика",)), ChatFilterConfig())
    return StreamDirector((queue, RateLimiter(interval_s)), stage, hold_s), stage


async def _next_or_none(
    director: StreamDirector, stream: AsyncGenerator[IncomingMessage]
) -> str | None:
    try:
        return (await asyncio.wait_for(anext(stream), TICK_S * 3)).text
    except TimeoutError:
        return None


async def test_mention_goes_first_and_stage_shows_it() -> None:
    director, stage = _director()
    director.add(_msg("просто так"))
    director.add(_msg("Мика, привет"))
    async with aclosing(director.selected()) as stream:
        assert (await anext(stream)).text == "Мика, привет"
    assert stage.log == ["question Мика, привет"]


async def test_channel_event_goes_before_messages_and_skips_filter() -> None:
    director, _ = _director()
    director.add(_msg("Мика, привет"))
    # Текст с «ссылкой» фильтр бы отбросил, но это слова Twitch, а не зрителя.
    director.add(IncomingMessage(EVENT_SOURCE, "Twitch", "Канал site.ru пришёл рейдом"))
    async with aclosing(director.selected()) as stream:
        assert (await anext(stream)).source == EVENT_SOURCE


async def test_rate_limit_holds_between_answers() -> None:
    director, _ = _director(interval_s=TICK_S * 5)
    director.add(_msg("раз"))
    director.add(_msg("два"))
    async with aclosing(director.selected()) as stream:
        await anext(stream)
        loop = asyncio.get_running_loop()
        started = loop.time()
        await anext(stream)
    assert loop.time() - started >= TICK_S * 4


async def test_pause_stops_answers_and_keeps_messages_until_resume() -> None:
    director, stage = _director()
    await director.pause()
    director.add(_msg("вопрос"))
    async with aclosing(director.selected()) as stream:
        pending = asyncio.ensure_future(anext(stream))
        await asyncio.sleep(TICK_S)
        assert not pending.done()
        await director.resume()
        assert (await asyncio.wait_for(pending, 1)).text == "вопрос"
    assert stage.log == ["paused", "live", "question вопрос"]


async def test_pause_while_waiting_for_message_is_respected() -> None:
    director, stage = _director()
    async with aclosing(director.selected()) as stream:
        pending = asyncio.ensure_future(anext(stream))
        await asyncio.sleep(0)
        await director.pause()
        director.add(_msg("вопрос"))
        await asyncio.sleep(TICK_S)
        assert not pending.done()
        await director.resume()
        assert (await asyncio.wait_for(pending, 1)).text == "вопрос"
    assert "question вопрос" in stage.log


async def test_host_reply_holds_chat_for_a_while() -> None:
    director, _ = _director(hold_s=TICK_S * 5)
    director.host_spoke()
    director.add(_msg("вопрос"))
    async with aclosing(director.selected()) as stream:
        assert await _next_or_none(director, stream) is None
    director2, _ = _director(hold_s=TICK_S)
    director2.host_spoke()
    director2.add(_msg("вопрос"))
    async with aclosing(director2.selected()) as stream:
        assert (await asyncio.wait_for(anext(stream), 1)).text == "вопрос"


class _Source:
    def __init__(self, *messages: IncomingMessage) -> None:
        self._messages = messages

    async def messages(self) -> AsyncGenerator[IncomingMessage]:
        for message in self._messages:
            yield message
        await asyncio.Event().wait()


async def _plugin(bus: EventBus, stage: _Stage) -> tuple[StreamDirectorPlugin, PluginContext]:
    settings = {"channel": "c", "host_hold_s": 60.0, "min_interval_s": 0}
    ctx = PluginContext("stream_director", bus, settings)
    plugin = StreamDirectorPlugin(_Source(_msg("вопрос")), stage)
    await plugin.setup(ctx)
    return plugin, ctx


async def test_plugin_registers_host_commands() -> None:
    stage = _Stage()
    plugin, ctx = await _plugin(EventBus(), stage)
    await ctx.commands["/пауза"]()
    await ctx.commands["/продолжай"]()
    await plugin.shutdown()
    assert stage.log == ["paused", "live"]


async def test_only_host_turn_holds_the_chat() -> None:
    bus = EventBus()
    plugin, ctx = await _plugin(bus, _Stage())
    pump = asyncio.create_task(ctx.run())
    viewer = Turn(TurnId(1), "зритель: привет", "Привет", is_external=True)
    await bus.publish(TurnRemembered(viewer, ()))
    await asyncio.sleep(0)
    async with aclosing(ctx.sources[0]()) as stream:
        assert (await asyncio.wait_for(anext(stream), 1)).text == "вопрос"
        await bus.publish(TurnRemembered(Turn(TurnId(2), "как дела", "Хорошо"), ()))
        await asyncio.sleep(0)
        assert plugin.director is not None
        plugin.director.add(_msg("ещё один"))
        assert await _next_or_none(plugin.director, stream) is None
    pump.cancel()
    await plugin.shutdown()


class _Obs:
    def __init__(self) -> None:
        self.requests: list[tuple[str, Mapping[str, object]]] = []

    async def request(self, request_type: str, data: Mapping[str, object]) -> None:
        self.requests.append((request_type, data))


async def test_obs_stage_switches_scene_and_shows_question() -> None:
    obs = _Obs()
    stage = ObsStage(obs, ("Эфир", "Перерыв"), "Вопрос")
    await stage.question(_msg("как дела"))
    await stage.paused()
    await stage.live()
    assert [name for name, _ in obs.requests] == [
        "SetInputSettings",
        "SetCurrentProgramScene",
        "SetInputSettings",
        "SetCurrentProgramScene",
    ]
    assert obs.requests[0][1]["inputSettings"] == {"text": "зритель: как дела"}
    assert obs.requests[1][1] == {"sceneName": "Перерыв"}
    assert obs.requests[2][1]["inputSettings"] == {"text": ""}


async def test_obs_stage_without_names_sends_nothing() -> None:
    obs = _Obs()
    stage = ObsStage(obs, ("", ""), "")
    await stage.paused()
    await stage.live()
    await stage.question(_msg("как дела"))
    assert obs.requests == []


def test_twitch_raid_notice_becomes_event() -> None:
    line = (
        r"@msg-id=raid;system-msg=15\sзрителей\sот\sa\sрейдят;display-name=a "
        ":tmi.twitch.tv USERNOTICE #chan"
    )
    event = parse_twitch_line(line, include_events=True)
    assert event == IncomingMessage(EVENT_SOURCE, "Twitch", "15 зрителей от a рейдят")
    assert parse_twitch_line(line, include_events=False) is None


def test_twitch_message_with_tags_is_still_a_message() -> None:
    line = "@badge-info=;color=#FF :viewer!viewer@viewer.tmi.twitch.tv PRIVMSG #chan :Привет"
    assert parse_twitch_line(line, include_events=True) == IncomingMessage(
        "twitch", "viewer", "Привет"
    )
