"""Помощник-программист на заглушке сервера: английский, код не в речь, отмена (S-12.6)."""

import asyncio
import json
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, aclosing, asynccontextmanager
from dataclasses import dataclass, field

import pytest

from vtuber.domain import TextShown
from vtuber.kernel import EventBus, LoadableModel, PluginContext
from vtuber_code_assistant import CodeAssistantPlugin, asks_for_code, texts_for

CODE = "def add(a, b):\n    return a + b\n"


@dataclass(slots=True)
class _Server:
    """OpenAI-совместимый сервер: отдаёт `reply` потоком, помнит запросы и обрыв."""

    reply: str
    status: str = "200 OK"
    hang: bool = False
    bodies: list[dict[str, object]] = field(default_factory=list)
    client_left: asyncio.Event = field(default_factory=asyncio.Event)

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        head = (await reader.readuntil(b"\r\n\r\n")).decode()
        length = int(head.lower().split("content-length: ")[1].split("\r\n")[0])
        self.bodies.append(json.loads(await reader.readexactly(length)))
        delta = json.dumps({"choices": [{"delta": {"content": self.reply}}]})
        body = f"data: {delta}\n\n" + ("" if self.hang else "data: [DONE]\n\n")
        writer.write(
            f"HTTP/1.1 {self.status}\r\nContent-Type: text/event-stream\r\n"
            f"Connection: close\r\n\r\n{body}".encode()
        )
        await writer.drain()
        if self.hang:
            await reader.read()
            self.client_left.set()
        writer.close()


@dataclass(slots=True)
class _World:
    plugin: CodeAssistantPlugin
    ctx: PluginContext
    main: _Server
    code: _Server
    shown: list[str]


@asynccontextmanager
async def _world(main: _Server, code: _Server, timeout_s: float = 5.0) -> AsyncIterator[_World]:
    main_srv = await asyncio.start_server(main.handle, "127.0.0.1", 0)
    code_srv = await asyncio.start_server(code.handle, "127.0.0.1", 0)
    settings = {
        "main_url": f"http://127.0.0.1:{main_srv.sockets[0].getsockname()[1]}",
        "code_url": f"http://127.0.0.1:{code_srv.sockets[0].getsockname()[1]}",
        "timeout_s": timeout_s,
    }
    bus = EventBus()
    shown: list[str] = []

    async def on_text(event: TextShown) -> None:
        shown.append(event.text)

    bus.subscribe(TextShown, on_text)
    ctx = PluginContext("code_assistant", bus, settings)
    plugin = CodeAssistantPlugin()
    await plugin.setup(ctx)
    try:
        yield _World(plugin, ctx, main, code, shown)
    finally:
        await plugin.shutdown()
        main_srv.close()
        code_srv.close()


async def _next_line(world: _World) -> str:
    async with aclosing(world.plugin.results()) as lines:
        message = await asyncio.wait_for(anext(lines), 5)
    assert message.is_viewer is False
    return message.text


@pytest.mark.parametrize(
    "text",
    ["Напиши функцию сортировки", "напиши мне код на питоне", "Помоги с кодом", "Исправь этот код"],
)
def test_explicit_request_is_recognized(text: str) -> None:
    assert asks_for_code(text)


@pytest.mark.parametrize(
    "text", ["Как дела?", "Я вчера писал код", "Напиши стихотворение", "код да Винчи"]
)
def test_ordinary_reply_is_not_a_task(text: str) -> None:
    assert not asks_for_code(text)


async def test_ordinary_reply_touches_nothing() -> None:
    async with _world(_Server("x"), _Server("y")) as world:
        assert await world.plugin.context("Как дела?") is None
    assert world.main.bodies == []
    assert world.code.bodies == []


async def test_task_goes_in_english_and_code_only_to_the_chat() -> None:
    async with _world(_Server("Write an add function"), _Server(CODE)) as world:
        hint = await world.plugin.context("Напиши функцию сложения")
        assert hint is not None
        assert "сама код не пиши" in hint
        line = await _next_line(world)
        await asyncio.sleep(0)

    assert world.code.bodies[0]["messages"][-1]["content"] == "Write an add function"  # type: ignore[index]
    assert world.main.bodies[0]["id_slot"] == 1, "перевод не должен занимать слот диалога"
    assert world.shown == [CODE]
    assert "def add" not in line, "в речь идёт только фраза, код остаётся в чате"
    assert "в чате" in line


async def test_second_task_waits_for_the_first() -> None:
    async with _world(_Server("x", hang=True), _Server(CODE)) as world:
        await world.plugin.context("Напиши код")
        hint = await world.plugin.context("Напиши код ещё раз")
    assert hint is not None
    assert "занят" in hint


async def test_cancel_closes_the_stream_so_the_server_stops() -> None:
    async with _world(_Server("Write it"), _Server("def", hang=True)) as world:
        await world.plugin.context("Напиши код")
        for _ in range(200):
            if world.code.bodies:
                break
            await asyncio.sleep(0.01)
        await world.ctx.commands["отмени код"]()
        await asyncio.wait_for(world.code.client_left.wait(), 5)
        assert await world.plugin.context("Напиши код") is not None
    assert world.shown == []


async def test_unavailable_model_is_said_honestly_and_nothing_breaks() -> None:
    async with _world(_Server("Write it"), _Server("", status="500 Oops")) as world:
        await world.plugin.context("Напиши код")
        line = await _next_line(world)
    assert "недоступен" in line
    assert world.shown == []


async def test_deadline_ends_the_task() -> None:
    async with _world(_Server("Write it"), _Server("def", hang=True), timeout_s=0.1) as world:
        await world.plugin.context("Напиши код")
        line = await _next_line(world)
    assert "срок" in line


@dataclass(slots=True)
class _Host:
    """Менеджер ресурсов: проверяем, что модель поднимают через него."""

    held: list[tuple[str, int]] = field(default_factory=list)
    used: int = 0

    def hold(
        self, name: str, vram_mb: int, model: LoadableModel
    ) -> Callable[[], AbstractAsyncContextManager[None]]:
        del model
        self.held.append((name, vram_mb))

        @asynccontextmanager
        async def use() -> AsyncIterator[None]:
            self.used += 1
            yield

        return use


async def test_own_server_goes_through_the_resource_manager() -> None:
    main, code = _Server("Write it"), _Server(CODE)
    main_srv = await asyncio.start_server(main.handle, "127.0.0.1", 0)
    code_srv = await asyncio.start_server(code.handle, "127.0.0.1", 0)
    host = _Host()
    server = {
        "autostart": False,
        "executable": "x.exe",
        "model": "m.gguf",
        "log_file": "l.log",
        "context_size": 1024,
        "slots": 1,
        "ready_timeout_s": 1.0,
        "stop_timeout_s": 1.0,
        "extra_args": (),
    }
    settings = {
        "main_url": f"http://127.0.0.1:{main_srv.sockets[0].getsockname()[1]}",
        "code_url": f"http://127.0.0.1:{code_srv.sockets[0].getsockname()[1]}",
        "vram_mb": 4321,
        "server": server,
    }
    ctx = PluginContext("code_assistant", EventBus(), settings, models=host)
    plugin = CodeAssistantPlugin()
    await plugin.setup(ctx)
    await plugin.context("Напиши код")
    async with aclosing(plugin.results()) as lines:
        await asyncio.wait_for(anext(lines), 5)
    await plugin.shutdown()
    main_srv.close()
    code_srv.close()
    assert host.held == [("code_assistant", 4321)]
    assert host.used == 1


def test_english_requests_are_recognised_and_not_translated() -> None:
    assert asks_for_code("Write me a function that sorts a list")
    assert asks_for_code("Can you help me with my code?")
    assert asks_for_code("fix this code please")
    assert not asks_for_code("Write me a poem")
    assert texts_for("en").translate is False
    assert texts_for("ru").translate is True
    assert texts_for("en").cancel == ("cancel code", "Cancel code")
