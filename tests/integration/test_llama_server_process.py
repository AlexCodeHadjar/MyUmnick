"""Запуск llama-server из ядра на поддельном сервере: тот же процесс, HTTP и остановка."""

import socket
import sys
from pathlib import Path

import httpx
import pytest

from vtuber.adapters.llm import LlamaServerConfig, LlamaServerProcess, server_arguments
from vtuber.domain import LLMUnavailable

FAKE_SERVER = """
import http.server, sys, time
args = sys.argv[1:]
port = int(args[args.index("--port") + 1])
time.sleep(float(args[0]))
if args[1] == "crash":
    sys.exit(7)

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
    def log_message(self, *a):
        pass

http.server.HTTPServer(("127.0.0.1", port), Handler).serve_forever()
"""


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _cfg(tmp_path: Path, *behaviour: str, **overrides: object) -> LlamaServerConfig:
    script = tmp_path / "fake_server.py"
    script.write_text(FAKE_SERVER, encoding="utf-8")
    values: dict[str, object] = {
        "autostart": True,
        "executable": Path(sys.executable),
        "model": Path("model.gguf"),
        "log_file": tmp_path / "logs" / "llama.log",
        "context_size": 16384,
        "slots": 2,
        "ready_timeout_s": 15.0,
        "stop_timeout_s": 5.0,
        "extra_args": (str(script), *behaviour),
    }
    return LlamaServerConfig.model_validate({**values, **overrides})


async def test_waits_until_ready_and_stops_with_context(tmp_path: Path) -> None:
    url = f"http://127.0.0.1:{_free_port()}"
    async with LlamaServerProcess(_cfg(tmp_path, "0.3", "ok"), url) as server:
        await server.wait_ready()
        async with httpx.AsyncClient() as client:
            assert (await client.get(url + "/health")).status_code == 200
    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.ConnectError):
            await client.get(url + "/health")
    assert (tmp_path / "logs").is_dir()


async def test_crash_is_reported_with_the_log_path(tmp_path: Path) -> None:
    url = f"http://127.0.0.1:{_free_port()}"
    async with LlamaServerProcess(_cfg(tmp_path, "0", "crash"), url) as server:
        with pytest.raises(LLMUnavailable, match="кодом 7"):
            await server.wait_ready()


async def test_slow_start_is_reported(tmp_path: Path) -> None:
    url = f"http://127.0.0.1:{_free_port()}"
    cfg = _cfg(tmp_path, "30", "ok", ready_timeout_s=0.3)
    async with LlamaServerProcess(cfg, url) as server:
        with pytest.raises(LLMUnavailable, match="не загрузил модель"):
            await server.wait_ready()


async def test_disabled_does_nothing(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path, "0", "ok", autostart=False)
    async with LlamaServerProcess(cfg, "http://127.0.0.1:9") as server:
        await server.wait_ready()
    assert not cfg.log_file.exists()


async def test_missing_executable_does_not_crash_the_app(tmp_path: Path) -> None:
    cfg = _cfg(tmp_path, "0", "ok", executable=tmp_path / "нет.exe")
    async with LlamaServerProcess(cfg, "http://127.0.0.1:9") as server:
        await server.wait_ready()


def test_arguments_match_the_start_script_and_config(tmp_path: Path) -> None:
    arguments = server_arguments(_cfg(tmp_path, "0", "ok"), "http://127.0.0.1:8081")
    for flag in ("--jinja", "--metrics", "--no-webui"):
        assert flag in arguments
    assert arguments[arguments.index("--port") + 1] == "8081"
    assert arguments[arguments.index("--parallel") + 1] == "2"
    assert arguments[arguments.index("--reasoning-budget") + 1] == "0"
