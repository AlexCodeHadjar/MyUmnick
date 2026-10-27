"""Сервер-заглушка OpenAI-совместимого API и llama-server на localhost: медленный SSE и обрыв."""

import asyncio
import json
from dataclasses import dataclass, field
from types import TracebackType
from typing import Final, Self

HEADER_END: Final = b"\r\n\r\n"
SSE_HEADERS: Final = (
    b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nConnection: close\r\n\r\n"
)
CHAT_PATH: Final = "/v1/chat/completions"
STUB_PROMPT: Final = "<|im_start|>user\nПривет<|im_end|>\n<|im_start|>assistant\n"
JSON_ANSWERS: Final[dict[str, object]] = {
    "/v1/models": {"data": [{"id": "stub"}]},
    "/apply-template": {"prompt": STUB_PROMPT},
    "/completion": {"content": ""},
}


@dataclass(slots=True)
class LLMStub:
    """Отдаёт `reply` порциями по `chunk_size` символов с паузой `delay_s` на запрос чата.

    `requests` — пары (путь, тело) всех запросов; `client_gone` — клиент оборвал стрим.
    """

    reply: str
    chunk_size: int = 3
    delay_s: float = 0.002
    requests: list[tuple[str, object]] = field(default_factory=list)
    client_gone: asyncio.Event = field(default_factory=asyncio.Event)
    _server: asyncio.Server | None = None

    @property
    def url(self) -> str:
        assert self._server is not None
        port = self._server.sockets[0].getsockname()[1]
        return f"http://127.0.0.1:{port}"

    def bodies(self, path: str) -> list[object]:
        """Тела запросов к `path` в порядке поступления."""
        return [body for request_path, body in self.requests if request_path == path]

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
            lengths = (
                int(line.split(":")[1])
                for line in head.splitlines()
                if line.lower().startswith("content-length")
            )
            body = await reader.readexactly(next(lengths, 0))
            self.requests.append((path, json.loads(body) if body else None))
            if path == CHAT_PATH:
                await self._stream_reply(reader, writer)
            else:
                await _answer_json(writer, JSON_ANSWERS[path])
        except ConnectionError:
            self.client_gone.set()
        finally:
            writer.close()

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


async def _answer_json(writer: asyncio.StreamWriter, answer: object) -> None:
    payload = json.dumps(answer, ensure_ascii=False).encode()
    writer.write(
        b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n"
        + f"Content-Length: {len(payload)}\r\n\r\n".encode()
        + payload
    )
    await writer.drain()


def _event(delta: dict[str, str]) -> bytes:
    chunk = {"choices": [{"index": 0, "delta": delta}]}
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode()
