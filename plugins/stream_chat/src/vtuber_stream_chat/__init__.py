"""Плагин чата стрима: сообщения зрителей становятся репликами витюбера (FR-14, S-12.2)."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import aclosing

from pydantic import Field

from vtuber.domain import IncomingMessage
from vtuber.kernel import ConfigSection, PluginContext
from vtuber.ports import MessageSource
from vtuber_stream_chat.selection import (
    ChatFilterConfig,
    ChatQueue,
    ChatQueueConfig,
    RateLimiter,
    passes_filter,
)
from vtuber_stream_chat.twitch import TwitchChat, parse_privmsg

__all__ = [
    "ChatFilterConfig",
    "ChatQueue",
    "ChatQueueConfig",
    "RateLimiter",
    "StreamChatConfig",
    "StreamChatPlugin",
    "TwitchChat",
    "parse_privmsg",
    "passes_filter",
]


class StreamChatConfig(ConfigSection):
    """Секция `[plugins.settings.stream_chat]`; обязателен только `channel`."""

    channel: str = Field(min_length=1)
    url: str = "wss://irc-ws.chat.twitch.tv:443"
    reconnect_s: float = Field(default=5.0, gt=0)
    min_interval_s: float = Field(default=20.0, ge=0)
    filter: ChatFilterConfig = ChatFilterConfig()
    queue: ChatQueueConfig = ChatQueueConfig()


class StreamChatPlugin:
    """Чат → фильтры и очередь → по одной выбранной реплике, не чаще лимита."""

    name = "stream_chat"

    def __init__(self, source: MessageSource | None = None) -> None:
        self._source = source
        self._reading: asyncio.Task[None] | None = None
        self._queue: ChatQueue | None = None
        self._limiter: RateLimiter | None = None

    async def setup(self, ctx: PluginContext) -> None:
        """Начать читать чат; выбранные реплики забирает ядро через источник."""
        cfg = ctx.settings(StreamChatConfig)
        source = self._source or TwitchChat(cfg.channel, cfg.url, cfg.reconnect_s)
        queue = ChatQueue(cfg.queue, cfg.filter)
        self._queue = queue
        self._limiter = RateLimiter(cfg.min_interval_s)
        self._reading = asyncio.create_task(self._read(source, queue, ctx))
        ctx.add_source(self.selected)

    async def shutdown(self) -> None:
        """Прекратить чтение чата."""
        if self._reading is not None:
            self._reading.cancel()
            await asyncio.wait({self._reading})

    async def selected(self) -> AsyncGenerator[IncomingMessage]:
        """Следующая реплика запрашивается, когда ядро готово на неё ответить."""
        if self._queue is None or self._limiter is None:
            return
        while True:
            await self._limiter.wait()
            message = await self._queue.next()
            self._limiter.mark()
            yield message

    async def _read(self, source: MessageSource, queue: ChatQueue, ctx: PluginContext) -> None:
        try:
            async with aclosing(source.messages()) as messages:
                async for message in messages:
                    queue.add(message)
        except Exception:
            ctx.log.exception("stream_chat.source_failed")
