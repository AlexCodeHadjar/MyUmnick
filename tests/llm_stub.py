"""Сервер-заглушка OpenAI-совместимого API на localhost: медленный SSE-стрим и учёт обрыва."""

import asyncio
import json
from dataclasses import dataclass, field
from types import TracebackType
from typing import Self

HEADER_END = b"\r\n\r\n"
SSE_HEADERS = b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nConnection: close\r\n\r\n"


@dataclass(slots=True)
class LLMStub:
    """Отдаёт `reply` порциями по `chunk_size` символов с паузой `delay_s` на каждый запрос чата.

    `requests` — тела запросов чата; `client_gone` — клиент закрыл соединение посреди стрима.
    """

    reply: str
    chunk_size: int = 3
    delay_s: float = 0.002
    requests: list[dict[str, object]] = field(default_factory=list)
    client_gone: asyncio.Event = field(default_factory=asyncio.Event)
    _server: asyncio.Server | None = None

    @property
    def url(self) -> str:
        assert self._server is not None
        port = self._server.sockets[0].getsockname()[1]
        return f"http://127.0.0.1:{port}"

    async def __aenter__(self) -> Self:
        self._server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        assert self._server is not None
        self._server.close()
        await self._server.wait_closed()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            head = (await reader.readuntil(HEADER_END)).decode()
            path = head.split(" ", 2)[1]
            length = next(
                (
                    int(line.split(":")[1])
                    for line in head.splitlines()
                    if line.lower().startswith("content-length")
                ),
                0,
            )
            body = await reader.readexactly(length)
            if path.endswith("/models"):
                await self._answer_models(writer)
            else:
                self.requests.append(json.loads(body))
                await self._stream_reply(reader, writer)
        except ConnectionError:
            self.client_gone.set()
        finally:
            writer.close()

    @staticmethod
    async def _answer_models(writer: asyncio.StreamWriter) -> None:
        payload = b'{"data": [{"id": "stub"}]}'
        writer.write(
            b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n"
            + f"Content-Length: {len(payload)}\r\n\r\n".encode()
            + payload
        )
        await writer.drain()

    async def _stream_reply(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        writer.write(SSE_HEADERS + _event({"role": "assistant"}))
        for start in range(0, len(self.reply), self.chunk_size):
            await asyncio.sleep(self.delay_s)
            if reader.at_eof():
                raise ConnectionResetError
            writer.write(_event({"content": self.reply[start : start + self.chunk_size]}))
            await writer.drain()
        writer.write(b"data: [DONE]\n\n")
        await writer.drain()


def _event(delta: dict[str, str]) -> bytes:
    chunk = {"choices": [{"index": 0, "delta": delta}]}
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode()
