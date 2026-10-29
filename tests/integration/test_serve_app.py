"""`python -m vtuber serve` целиком: шлюз, статус LLM, ход по WebSocket, выход по концу stdin."""

import asyncio
import io
import json
import socket
import threading
from pathlib import Path

import pytest
import structlog
from websockets.asyncio.client import ClientConnection, connect

from tests.llm_stub import LLMStub
from vtuber.bootstrap import Console, main
from vtuber.gateway import decode_audio_frame

ROOT = Path(__file__).resolve().parents[2]
SEND = json.dumps({"v": 1, "type": "chat.send", "data": {"text": "Привет"}})


class _HeldStdin:
    """stdin, который не кончается, пока тест не «закроет» его (как pipe от Tauri)."""

    def __init__(self) -> None:
        self.closed_by_parent = threading.Event()

    def readline(self) -> str:
        self.closed_by_parent.wait()
        return ""


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


async def _connect(port: int) -> ClientConnection:
    for _ in range(200):
        try:
            return await connect(f"ws://127.0.0.1:{port}")
        except OSError:
            await asyncio.sleep(0.02)
    msg = f"Шлюз не поднялся на порту {port}"
    raise TimeoutError(msg)


async def _until(ws: ClientConnection, kind: str, state: str | None = None) -> dict[str, object]:
    while True:
        message: dict[str, object] = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        data = message["data"]
        if message["type"] == kind and (
            state is None or (isinstance(data, dict) and data["state"] == state)
        ):
            return message


async def test_serve_mode_runs_gateway_until_stdin_closes(tmp_path: Path) -> None:
    port, stdin, out = _free_port(), _HeldStdin(), io.StringIO()

    async with LLMStub("<happy>Привет!", chunk_size=4, delay_s=0) as stub:
        env = {
            "VTUBER_LLM__BASE_URL": stub.url,
            "VTUBER_GATEWAY__PORT": str(port),
            "VTUBER_LOGGING__FILE": str(tmp_path / "app.jsonl"),
            "VTUBER_TELEMETRY__TRACES_FILE": str(tmp_path / "traces.jsonl"),
            "VTUBER_TTS__BACKEND": "none",
            "VTUBER_MEMORY__ENABLED": "false",
        }
        app = asyncio.create_task(
            asyncio.to_thread(main, ["serve", "--root", str(ROOT)], env, Console(stdin, out))
        )
        ws = await _connect(port)
        await _until(ws, "status", "ready")
        await ws.send(SEND)
        finished = await _until(ws, "turn.finished")
        await ws.close()
        stdin.closed_by_parent.set()
        code = await asyncio.wait_for(app, timeout=5)
    structlog.reset_defaults()

    assert finished["turn"] == "t-000001"
    assert code == 0
    assert f"ws://127.0.0.1:{port}" in out.getvalue()


async def test_serve_mode_keeps_running_when_llm_is_down(tmp_path: Path) -> None:
    port, stdin, out = _free_port(), _HeldStdin(), io.StringIO()
    env = {
        "VTUBER_LLM__BASE_URL": "http://127.0.0.1:9",
        "VTUBER_LLM__CONNECT_TIMEOUT_S": "0.2",
        "VTUBER_GATEWAY__PORT": str(port),
        "VTUBER_LOGGING__FILE": str(tmp_path / "app.jsonl"),
        "VTUBER_TELEMETRY__TRACES_FILE": str(tmp_path / "traces.jsonl"),
        "VTUBER_TTS__BACKEND": "none",
        "VTUBER_MEMORY__ENABLED": "false",
    }
    app = asyncio.create_task(
        asyncio.to_thread(main, ["serve", "--root", str(ROOT)], env, Console(stdin, out))
    )
    ws = await _connect(port)
    await _until(ws, "status", "failed")
    await ws.close()
    stdin.closed_by_parent.set()

    assert await asyncio.wait_for(app, timeout=5) == 0
    assert "llm.unavailable_at_start" in (tmp_path / "app.jsonl").read_text(encoding="utf-8")


SILERO_MODEL = ROOT / "models" / "tts" / "silero" / "v5_6_ru.pt"


@pytest.mark.slow
@pytest.mark.skipif(not SILERO_MODEL.is_file(), reason=f"нет модели Silero {SILERO_MODEL}")
async def test_serve_mode_speaks_reply_as_binary_audio_frames(tmp_path: Path) -> None:
    port, stdin, out = _free_port(), _HeldStdin(), io.StringIO()

    async with LLMStub("<happy>Привет! Рада тебя видеть.", chunk_size=4, delay_s=0) as stub:
        env = {
            "VTUBER_LLM__BASE_URL": stub.url,
            "VTUBER_GATEWAY__PORT": str(port),
            "VTUBER_LOGGING__FILE": str(tmp_path / "app.jsonl"),
            "VTUBER_TELEMETRY__TRACES_FILE": str(tmp_path / "traces.jsonl"),
            "VTUBER_MEMORY__ENABLED": "false",
        }
        app = asyncio.create_task(
            asyncio.to_thread(main, ["serve", "--root", str(ROOT)], env, Console(stdin, out))
        )
        ws = await _connect(port)
        frames, statuses = await _speak_once(ws)
        await ws.close()
        stdin.closed_by_parent.set()
        code = await asyncio.wait_for(app, timeout=10)
    structlog.reset_defaults()

    assert ("tts", "ready") in statuses
    assert frames
    decoded = [decode_audio_frame(frame) for frame in frames]
    assert [frame.seq for frame in decoded] == list(range(len(decoded)))
    assert {frame.chunk.format.sample_rate for frame in decoded} == {48000}
    assert sum(frame.chunk.duration_s for frame in decoded) > 1.0
    assert code == 0


async def _speak_once(ws: ClientConnection) -> tuple[list[bytes], list[tuple[str, str]]]:
    """Ждёт готовности LLM и TTS, шлёт реплику, собирает звук до `turn.finished`."""
    frames: list[bytes] = []
    statuses: list[tuple[str, str]] = []
    sent = False
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=30)
        if isinstance(raw, bytes):
            frames.append(raw)
            continue
        message = json.loads(raw)
        if message["type"] == "status":
            statuses.append((message["data"]["component"], message["data"]["state"]))
        if not sent and {("llm", "ready"), ("tts", "ready")} <= set(statuses):
            await ws.send(SEND)
            sent = True
        if message["type"] == "turn.finished":
            return frames, statuses
