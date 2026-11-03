"""Самовосстановление на настоящем `serve`: падение сервера в ответе и жёстко убитое ядро (S-17.1).

Вместо llama-server — заглушка на том же порту: запускается и умирает как настоящий процесс.
"""

import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from websockets.asyncio.client import ClientConnection, connect

ROOT = Path(__file__).resolve().parents[2]
SEND = json.dumps({"v": 1, "type": "chat.send", "data": {"text": "Привет"}})
FAKE_SERVER = """
import asyncio, os, sys
sys.path.insert(0, sys.argv[1])
from tests.llm_stub import LLMStub

args = sys.argv
port = int(args[args.index("--port") + 1])

async def main():
    with open(args[2], "a") as pids:
        pids.write(f"{os.getpid()}\\n")
    async with LLMStub("Длинный ответ. " * 40, chunk_size=4, delay_s=0.02, port=port):
        await asyncio.Event().wait()

asyncio.run(main())
"""
USER_TOML = """
[llama_server]
autostart = true
executable = {python}
model = "model.gguf"
extra_args = [{script}, {root}, {pids}]

[supervisor]
check_s = 0.2
health_timeout_s = 1.0
backoff_s = 0.1
"""


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _alive(pid: int) -> bool:
    # os.kill(pid, 0) на Windows не проверяет процесс, а завершает его.
    result = subprocess.run(  # noqa: S603
        ["tasklist", "/FI", f"PID eq {pid}", "/NH"],  # noqa: S607
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )
    return str(pid) in result.stdout


def _prepare(root: Path) -> None:
    shutil.copytree(ROOT / "config", root / "config")
    shutil.copytree(ROOT / "personas", root / "personas")
    (root / "model.gguf").write_bytes(b"")
    (root / "fake_server.py").write_text(FAKE_SERVER, encoding="utf-8")
    (root / "config" / "user.toml").write_text(
        USER_TOML.format(
            python=json.dumps(sys.executable),
            script=json.dumps(str(root / "fake_server.py")),
            root=json.dumps(str(ROOT)),
            pids=json.dumps(str(root / "pids.txt")),
        ),
        encoding="utf-8",
    )


def _server_pids(root: Path) -> list[int]:
    return [int(line) for line in (root / "pids.txt").read_text().split()]


async def _until(ws: ClientConnection, kind: str, **fields: str) -> dict[str, object]:
    async with asyncio.timeout(60):
        while True:
            raw = await ws.recv()
            if isinstance(raw, bytes):
                continue
            message: dict[str, object] = json.loads(raw)
            data = message["data"]
            if message["type"] == kind and all(
                isinstance(data, dict) and data.get(k) == v for k, v in fields.items()
            ):
                return message


async def _connect(port: int) -> ClientConnection:
    for _ in range(600):
        try:
            return await connect(f"ws://127.0.0.1:{port}")
        except OSError:
            await asyncio.sleep(0.05)
    raise TimeoutError


def _kill(pid: int) -> None:
    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, check=True)  # noqa: S603, S607


def _env(port: int) -> dict[str, str]:
    return {
        **os.environ,
        "VTUBER_GATEWAY__PORT": str(port),
        "VTUBER_LLM__BASE_URL": f"http://127.0.0.1:{_free_port()}",
        "VTUBER_TTS__BACKEND": "none",
        "VTUBER_MEMORY__ENABLED": "false",
        "VTUBER_STT__ENABLED": "false",
    }


async def _crash_during_reply_and_recover(ws: ClientConnection, root: Path) -> int:
    """Возвращает номер процесса нового сервера."""
    await _until(ws, "status", component="llm", state="ready")
    first = _server_pids(root)[-1]

    # Падение посреди ответа: ход кончается понятной ошибкой, приложение живёт.
    await ws.send(SEND)
    await _until(ws, "chat.delta")
    _kill(first)
    cancelled = await _until(ws, "turn.cancelled", reason="error")
    assert cancelled["data"]["message"]  # type: ignore[index]

    # Наблюдатель поднимает сервер сам, а чат снова работает.
    notice = await _until(ws, "backend.notice")
    assert "перезапускается" in str(notice["data"])
    await _until(ws, "status", component="llm", state="ready")
    second = _server_pids(root)[-1]
    assert second != first
    await ws.send(SEND)
    await _until(ws, "turn.finished")
    return second


@pytest.mark.slow
@pytest.mark.skipif(sys.platform != "win32", reason="связь с ядром через Job Object")
async def test_killed_server_recovers_and_killed_core_leaves_no_server(tmp_path: Path) -> None:
    _prepare(tmp_path)
    port = _free_port()
    core = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "vtuber", "serve", "--root", str(tmp_path),
        stdin=asyncio.subprocess.PIPE, env=_env(port),
    )  # fmt: skip
    try:
        ws = await _connect(port)
        server = await _crash_during_reply_and_recover(ws, tmp_path)
        await ws.close()

        # Ядро убито жёстко: штатный выход не сработает, а сервер всё равно не остаётся.
        assert _alive(server)
        core.kill()
        await core.wait()
        for _ in range(50):
            if not _alive(server):
                break
            await asyncio.sleep(0.1)
        assert not _alive(server)
    finally:
        if core.returncode is None:
            core.kill()
            await core.wait()
