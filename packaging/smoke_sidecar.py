"""Дымовая проверка сборки и замер холодного старта (ADR-0019, NFR-07).

Настоящие модели голоса, памяти и слуха, заглушка вместо LLM (`tests/llm_stub.py`). Проверяет то,
что в собранном приложении ломается первым: динамические импорты, DLL, данные пакетов, entry points.

`PYTHONPATH=. uv run python packaging/smoke_sidecar.py [--python]`; с `--python` — без сборки, для
сравнения. Модулем не запускать: имя каталога совпадает с пакетом `packaging` из PyPI.
"""

import argparse
import asyncio
import json
import os
import shutil
import socket
import sys
import tempfile
import time
import wave
from pathlib import Path
from typing import Final

from websockets.asyncio.client import ClientConnection, connect

from tests.llm_stub import LLMStub
from vtuber.domain import AudioChunk, AudioFormat
from vtuber.gateway import encode_mic_frame

ROOT: Final = Path(__file__).resolve().parent.parent
EXE: Final = ROOT / "packaging" / "dist" / "vtuber-core" / "vtuber-core.exe"
SPEECH: Final = ROOT / "tests" / "data" / "speech_ru_16k.wav"
FRAME_SAMPLES: Final = 512
SAMPLE_BYTES: Final = 2
SILENCE_S: Final = 1.5
USER_TOML: Final = """
[plugins]
enabled = ["tools", "obs", "stream_chat", "stream_director"]

[plugins.settings.stream_chat]
channel = "smoke"
url = "ws://127.0.0.1:9"

[plugins.settings.stream_director]
channel = "smoke"
url = "ws://127.0.0.1:9"

[plugins.settings.obs]
url = "ws://127.0.0.1:9"
"""


def _prepare_root(root: Path) -> None:
    """Конфиг и персоны — во временном корне; пути моделей ведут в репозиторий."""
    shutil.copytree(ROOT / "config", root / "config")
    shutil.copytree(ROOT / "personas", root / "personas")
    default = root / "config" / "default.toml"
    models = (ROOT / "models").as_posix()
    text = default.read_text(encoding="utf-8").replace('"models/', f'"{models}/')
    default.write_text(text, encoding="utf-8")
    (root / "config" / "user.toml").write_text(USER_TOML, encoding="utf-8")


def _command(*, python: bool, root: Path) -> list[str]:
    start = [sys.executable, "-m", "vtuber"] if python else [str(EXE)]
    return [*start, "serve", "--root", str(root)]


async def _connect(port: int) -> ClientConnection:
    while True:
        try:
            return await connect(f"ws://127.0.0.1:{port}", max_size=None)
        except OSError:
            await asyncio.sleep(0.02)


async def _until(
    ws: ClientConnection, kind: str, component: str | None = None
) -> dict[str, object]:
    while True:
        raw = await asyncio.wait_for(ws.recv(), 120)
        if isinstance(raw, bytes):
            continue
        message: dict[str, object] = json.loads(raw)
        data = message["data"]
        if message["type"] != kind:
            continue
        if component is None or (data["component"] == component and data["state"] == "ready"):  # type: ignore[index]
            return message


async def _audio_frames_until_finished(ws: ClientConnection) -> int:
    frames = 0
    while True:
        raw = await asyncio.wait_for(ws.recv(), 120)
        if isinstance(raw, bytes):
            frames += 1
        elif json.loads(raw)["type"] == "turn.finished":
            return frames


async def _say_into_microphone(ws: ClientConnection) -> None:
    with wave.open(str(SPEECH), "rb") as speech:
        rate = speech.getframerate()
        pcm = speech.readframes(speech.getnframes())
    pcm += b"\x00" * int(SILENCE_S * rate) * SAMPLE_BYTES
    step = FRAME_SAMPLES * SAMPLE_BYTES
    for seq, start in enumerate(range(0, len(pcm) - step, step)):
        chunk = AudioChunk(AudioFormat(sample_rate=rate), pcm[start : start + step])
        await ws.send(encode_mic_frame(seq, chunk))
        await asyncio.sleep(FRAME_SAMPLES / rate / 4)


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


async def _full_check(ws: ClientConnection, started: float) -> None:
    send = {"v": 1, "type": "chat.send", "data": {"text": "Который час?"}}
    await ws.send(json.dumps(send))
    print(f"звуковых кадров в ответе: {await _audio_frames_until_finished(ws)}")
    await _say_into_microphone(ws)
    await _until(ws, "status", "stt")
    print(f"слух готов: {time.perf_counter() - started:.1f} с")
    final = await _until(ws, "input.final")
    print("распознано:", json.dumps(final["data"], ensure_ascii=True))


async def _scenario(command: list[str], *, start_only: bool) -> None:
    port = _free_port()
    async with LLMStub("<happy>Привет, это проверка сборки.", chunk_size=6, delay_s=0) as stub:
        env_values = {"VTUBER_LLM__BASE_URL": stub.url, "VTUBER_GATEWAY__PORT": str(port)}
        started = time.perf_counter()
        process = await asyncio.create_subprocess_exec(
            *command, stdin=asyncio.subprocess.PIPE, env={**os.environ, **env_values}
        )
        try:
            ws = await _connect(port)
            print(f"шлюз открыт: {time.perf_counter() - started:.1f} с")
            await _until(ws, "status", "tts")
            print(f"голос готов: {time.perf_counter() - started:.1f} с")
            if not start_only:
                await _full_check(ws, started)
            await ws.close()
        finally:
            if process.stdin is not None:
                process.stdin.close()
            print(f"код выхода: {await asyncio.wait_for(process.wait(), 60)}")


def _log_events(root: Path) -> list[dict[str, object]]:
    path = root / "logs" / "app.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def main() -> int:
    """0 — все проверки сценария прошли; сбой — исключение."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", action="store_true", help="без сборки, для сравнения")
    parser.add_argument("--start-only", action="store_true", help="только замер старта")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        root = Path(tmp)
        _prepare_root(root)
        command = _command(python=args.python, root=root)
        asyncio.run(_scenario(command, start_only=args.start_only))
        wanted = ("plugin.", "memory.background_ready", "tts.ready", "voice.ready")
        for entry in _log_events(root):
            event = str(entry["event"])
            if event.startswith(wanted) or entry["level"] == "error":
                print(json.dumps({"event": event, "plugin": entry.get("plugin")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
