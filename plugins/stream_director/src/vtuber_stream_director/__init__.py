"""Плагин режиссёра стрима: чат, паузы, реакции, сцены OBS, перехват ведущим (FR-27, S-12.8)."""

import asyncio
from contextlib import aclosing

from pydantic import Field

from vtuber.domain import TurnRemembered, looks_like_attack
from vtuber.kernel import ConfigSection, PluginContext
from vtuber.ports import MessageSource
from vtuber_obs import ObsClient
from vtuber_stream_chat import ChatFilterConfig, ChatQueue, ChatQueueConfig, RateLimiter, TwitchChat
from vtuber_stream_director.director import ObsStage, Stage, StreamDirector

__all__ = ["DirectorConfig", "ObsLink", "ObsStage", "StreamDirector", "StreamDirectorPlugin"]


class ObsLink(ConfigSection):
    """Подсекция `obs`: сцены эфира и паузы, текстовый источник с вопросом; пусто — без действия."""

    url: str = "ws://127.0.0.1:4455"
    password: str = ""
    reconnect_s: float = Field(default=5.0, gt=0)
    live_scene: str = ""
    paused_scene: str = ""
    question_input: str = ""


class DirectorConfig(ConfigSection):
    """Секция `[plugins.settings.stream_director]`; обязателен только `channel`."""

    channel: str = Field(min_length=1)
    url: str = "wss://irc-ws.chat.twitch.tv:443"
    reconnect_s: float = Field(default=5.0, gt=0)
    min_interval_s: float = Field(default=20.0, ge=0)
    host_hold_s: float = Field(default=30.0, ge=0)
    pause_command: str = "/пауза"
    resume_command: str = "/продолжай"
    filter: ChatFilterConfig = ChatFilterConfig()
    queue: ChatQueueConfig = ChatQueueConfig()
    obs: ObsLink = ObsLink()


class StreamDirectorPlugin:
    """Собирает режиссёра; вместе с плагином `stream_chat` не включается: ответы задвоятся."""

    name = "stream_director"

    def __init__(self, source: MessageSource | None = None, stage: Stage | None = None) -> None:
        self._source = source
        self._stage = stage
        self._tasks: list[asyncio.Task[None]] = []
        self.director: StreamDirector | None = None

    async def setup(self, ctx: PluginContext) -> None:
        """Подключить чат и OBS; без OBS режиссёр работает, сцена просто не меняется."""
        cfg = ctx.settings(DirectorConfig)
        source = self._source or TwitchChat(
            cfg.channel, cfg.url, cfg.reconnect_s, include_events=True
        )
        director = StreamDirector(
            (ChatQueue(cfg.queue, cfg.filter), RateLimiter(cfg.min_interval_s)),
            self._stage or self._obs_stage(cfg.obs),
            cfg.host_hold_s,
        )
        self.director = director
        self._tasks.append(asyncio.create_task(self._read(source, director, ctx)))
        ctx.add_source(director.selected)
        ctx.add_command(cfg.pause_command, director.pause)
        ctx.add_command(cfg.resume_command, director.resume)

        async def on_turn(event: TurnRemembered) -> None:
            if not event.turn.is_external:
                director.host_spoke()

        ctx.subscribe(TurnRemembered, on_turn)

    async def shutdown(self) -> None:
        """Остановить чтение чата и соединение с OBS."""
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.wait(self._tasks)

    def _obs_stage(self, link: ObsLink) -> ObsStage:
        client = ObsClient(link.url, link.password, link.reconnect_s)
        self._tasks.append(asyncio.create_task(client.run()))
        return ObsStage(client, (link.live_scene, link.paused_scene), link.question_input)

    async def _read(
        self, source: MessageSource, director: StreamDirector, ctx: PluginContext
    ) -> None:
        try:
            async with aclosing(source.messages()) as messages:
                async for message in messages:
                    # Атака не занимает очередь: иначе зритель тратил бы лимит частоты впустую.
                    if looks_like_attack(message.text):
                        await ctx.report_blocked(message.author, message.text)
                    else:
                        director.add(message)
        except Exception:
            ctx.log.exception("stream_director.source_failed")
