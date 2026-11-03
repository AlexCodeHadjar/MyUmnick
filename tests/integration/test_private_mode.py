"""Приватный режим на настоящем `serve`: на диске нет ни слова, очистка удаляет всё (S-17.2)."""

import asyncio
import io
import json
import socket
import threading
from pathlib import Path

import pytest
import structlog
from websockets.asyncio.client import ClientConnection, connect

from tests.contract.memory_factories import E5_DIR
from tests.llm_stub import LLMStub
from vtuber.bootstrap import Console, main

ROOT = Path(__file__).resolve().parents[2]
SECRET = "ЗЕЛЁНЫЙСЛОНСЕКРЕТ"  # noqa: S105 — слово, которого не должно быть на диске
PUBLIC = "МЕНЯЗОВУТОБЫЧНОЕСЛОВО"
FACTS = '{"facts": [{"text": "Обычный факт о ведущем", "importance": 1}]}'


class _Held:
    def __init__(self) -> None:
        self.closed = threading.Event()

    def readline(self) -> str:
        self.closed.wait()
        return ""


def _say(text: str) -> str:
    return json.dumps({"v": 1, "type": "chat.send", "data": {"text": text}})


def _private(*, enabled: bool) -> str:
    return json.dumps({"v": 1, "type": "privacy.set", "data": {"enabled": enabled}})


def _erase(*, confirm: bool) -> str:
    return json.dumps({"v": 1, "type": "memory.erase", "data": {"confirm": confirm}})


async def _until(ws: ClientConnection, kind: str) -> dict[str, object]:
    async with asyncio.timeout(30):
        while True:
            message: dict[str, object] = json.loads(await ws.recv())
            if message["type"] == kind:
                return message


async def _connect(port: int) -> ClientConnection:
    for _ in range(600):
        try:
            return await connect(f"ws://127.0.0.1:{port}")
        except OSError:
            await asyncio.sleep(0.05)
    raise TimeoutError


def _everything_on_disk(root: Path) -> bytes:
    return b"".join(path.read_bytes() for path in root.rglob("*") if path.is_file())


def _env(tmp_path: Path, url: str, port: int) -> dict[str, str]:
    return {
        "VTUBER_LLM__BASE_URL": url,
        "VTUBER_GATEWAY__PORT": str(port),
        "VTUBER_LOGGING__FILE": str(tmp_path / "logs" / "app.jsonl"),
        "VTUBER_LOGGING__LEVEL": "DEBUG",
        "VTUBER_TELEMETRY__TRACES_FILE": str(tmp_path / "logs" / "traces.jsonl"),
        "VTUBER_MEMORY__STORE_PATH": str(tmp_path / "facts.sqlite"),
        "VTUBER_MEMORY__VAULT_PATH": str(tmp_path / "vault"),
        "VTUBER_MEMORY__VAULT_POLL_S": "0.2",
        "VTUBER_SCHEDULER__IDLE_AFTER_MS": "50",
        "VTUBER_TTS__BACKEND": "none",
        "VTUBER_STT__ENABLED": "false",
    }


async def _private_talk(ws: ClientConnection, tmp_path: Path) -> None:
    state = await _until(ws, "privacy.state")
    assert state["data"] == {"enabled": False, "erasable": True}

    await ws.send(_private(enabled=True))
    assert (await _until(ws, "privacy.state"))["data"] == {"enabled": True, "erasable": True}
    await ws.send(_say(f"Мой секрет: {SECRET}"))
    await _until(ws, "turn.finished")
    await asyncio.sleep(1.0)  # простой: фон успел бы записать факт и чат
    assert SECRET.encode() not in _everything_on_disk(tmp_path)
    assert not list((tmp_path / "vault" / "Факты").glob("*.md"))

    await ws.send(_private(enabled=False))
    await ws.send(_say(f"Обычная реплика {PUBLIC}"))
    await _until(ws, "turn.finished")
    await asyncio.sleep(1.5)
    disk = _everything_on_disk(tmp_path)
    assert PUBLIC.encode() in disk  # память до и после режима работает как прежде
    assert SECRET.encode() not in disk
    assert list((tmp_path / "vault" / "Факты").glob("*.md"))


async def _erase_everything(ws: ClientConnection, tmp_path: Path) -> None:
    await ws.send(_erase(confirm=False))
    assert (await _until(ws, "memory.erased"))["data"] != {"problem": None}
    assert list((tmp_path / "vault" / "Факты").glob("*.md"))

    await ws.send(_erase(confirm=True))
    assert (await _until(ws, "memory.erased"))["data"] == {"problem": None}
    assert not list((tmp_path / "vault").rglob("*.md"))
    await asyncio.sleep(0.5)
    assert "Обычный факт".encode() not in (tmp_path / "facts.sqlite").read_bytes()


@pytest.mark.slow
@pytest.mark.skipif(not (E5_DIR / "model.onnx").is_file(), reason=f"нет модели e5 в {E5_DIR}")
async def test_private_talk_leaves_no_trace_and_erase_removes_everything(tmp_path: Path) -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = int(probe.getsockname()[1])
    stdin = _Held()
    async with LLMStub(FACTS, chunk_size=16, delay_s=0) as stub:
        env = _env(tmp_path, stub.url, port)
        console = Console(stdin, io.StringIO())
        app = asyncio.create_task(
            asyncio.to_thread(main, ["serve", "--root", str(ROOT)], env, console)
        )
        try:
            async with await _connect(port) as ws:
                await _private_talk(ws, tmp_path)
                await _erase_everything(ws, tmp_path)
        finally:
            stdin.closed.set()
            await asyncio.wait_for(app, 30)
    structlog.reset_defaults()
    assert SECRET.encode() not in _everything_on_disk(tmp_path)
