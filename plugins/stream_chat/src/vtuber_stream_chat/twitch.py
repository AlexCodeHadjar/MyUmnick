"""Чат Twitch через IRC по WebSocket: анонимное чтение, без аккаунта и ключей."""

import asyncio
import re
import secrets
from collections.abc import AsyncGenerator
from typing import Final

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed

from vtuber.domain import IncomingMessage
from vtuber.kernel import get_logger

SOURCE_NAME: Final = "twitch"
_PRIVMSG: Final = re.compile(r"^:(?P<author>[^!\s]+)!\S+ PRIVMSG #\S+ :(?P<text>.*)$")
_PING: Final = "PING"
_ANONYMOUS_NICK_LIMIT: Final = 100_000

_log = get_logger(__name__)


def parse_privmsg(line: str) -> IncomingMessage | None:
    """Сообщение чата из строки IRC; служебные строки — None."""
    match = _PRIVMSG.match(line.rstrip("\r\n"))
    if match is None:
        return None
    return IncomingMessage(SOURCE_NAME, match["author"], match["text"])


class TwitchChat:
    """`MessageSource`: читает канал; разрыв — новое подключение через `reconnect_s`."""

    def __init__(self, channel: str, url: str, reconnect_s: float) -> None:
        self._channel = channel.removeprefix("#").lower()
        self._url = url
        self._reconnect_s = reconnect_s

    async def messages(self) -> AsyncGenerator[IncomingMessage]:
        """Реплики канала, пока генератор не закроют."""
        while True:
            try:
                async with connect(self._url) as ws:
                    await self._join(ws)
                    async for message in self._read(ws):
                        yield message
            except (OSError, ConnectionClosed, TimeoutError) as exc:
                _log.warning("twitch.disconnected", problem=str(exc))
            await asyncio.sleep(self._reconnect_s)

    async def _join(self, ws: ClientConnection) -> None:
        # justinfan<число> — анонимный вход Twitch только для чтения: пароль не нужен.
        await ws.send("PASS SCHMOOPIIE")
        await ws.send(f"NICK justinfan{secrets.randbelow(_ANONYMOUS_NICK_LIMIT)}")
        await ws.send(f"JOIN #{self._channel}")
        _log.info("twitch.joined", channel=self._channel)

    async def _read(self, ws: ClientConnection) -> AsyncGenerator[IncomingMessage]:
        async for frame in ws:
            for line in str(frame).splitlines():
                if line.startswith(_PING):
                    await ws.send(f"PONG{line[len(_PING) :]}")
                elif (message := parse_privmsg(line)) is not None:
                    yield message
