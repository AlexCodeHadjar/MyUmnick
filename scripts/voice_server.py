"""Сервер голоса OmniVoice (ADR-0031): фраза по HTTP, PCM s16le 24 кГц в ответ.

Запускается в своём окружении на Linux (арендованная машина или WSL2), в зависимости проекта не
входит: нужны omnivoice из git, torch под CUDA пакета и FlashInfer. Слушает только localhost.
GET /health — готовность и частота; POST /synthesize {"text": "..."} — звук фразы.

    python scripts/voice_server.py --ref data/voice_refs/silv/prepared/maomao_04.wav \
        --ref-text data/voice_refs/silv/prepared/refs.json

Голос реального человека: использовать только в границах его разрешения (ADR-0031).
"""

# Отдельный процесс без проекта: зависимости импортируются при запуске, в журнал пишет print.
# ruff: noqa: D102, D103, INP001, ISC004, PLC0415, T201

from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

SAMPLE_RATE = 24000
MAX_BODY_BYTES = 64 * 1024
# CUDA Graph готовится на каждую новую длину 0,6–1,4 с: платим при запуске, а не в разговоре (T-06).
WARMUP = (
    "Хм.",
    "Хм, интересно.",
    "Сейчас посмотрю, что тут у нас.",
    "Привет! Я рада, что ты заглянул. Как прошёл твой день?",
    "Нет, правда? Вот это да! Ни за что бы не подумала, что так получится!",
    "Знаешь, вчера я весь вечер читала про лекарственные травы, и теперь могу рассказать, "
    "чем ромашка отличается от пижмы.",
    "Если коротко, всё зависит от того, что именно ты хочешь получить в итоге, сколько у тебя "
    "есть времени и готов ли ты разбираться в деталях самостоятельно, не спеша.",
)


class Voice:
    """Модель и разобранный образец; синтез строго по одному."""

    def __init__(self, args: argparse.Namespace) -> None:
        import torch
        from omnivoice import OmniVoice

        self._steps = args.steps
        self._lock = threading.Lock()
        self._model: Any = OmniVoice.from_pretrained(
            "k2-fsa/OmniVoice", device_map="cuda:0", dtype=torch.float16
        )
        if args.flash:
            from omnivoice.models.omnivoice_flashinfer import apply_flashinfer

            apply_flashinfer(self._model, enable_cuda_graph=True)
        ref = Path(args.ref)
        refs = json.loads(Path(args.ref_text).read_text(encoding="utf-8"))
        self._prompt = self._model.create_voice_clone_prompt(
            ref_audio=str(ref), ref_text=refs[ref.name]
        )

    def warm_up(self) -> None:
        for text in WARMUP:
            started = time.perf_counter()
            self.synthesize(text)
            print(f"прогрев {time.perf_counter() - started:.2f} с: {len(text)} симв.", flush=True)

    def synthesize(self, text: str) -> bytes:
        import numpy as np

        with self._lock:
            wav = self._model.generate(
                text=text,
                language="Russian",
                voice_clone_prompt=self._prompt,
                num_step=self._steps,
            )[0]
        pcm = np.clip(np.asarray(wav, dtype=np.float32), -1.0, 1.0) * 32767
        return pcm.astype(np.int16).tobytes()


def handler_for(voice: Voice) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:
            if self.path == "/health":
                body = json.dumps({"status": "ok", "sample_rate": SAMPLE_RATE}).encode()
                self._reply(200, body, "application/json")
            else:
                self._reply(404, b"", "text/plain")

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", 0))
            if self.path != "/synthesize" or length > MAX_BODY_BYTES:
                self._reply(400, b"", "text/plain")
                return
            try:
                text = json.loads(self.rfile.read(length))["text"]
                started = time.perf_counter()
                pcm = voice.synthesize(text)
            except Exception as error:  # noqa: BLE001 — ответ клиенту вместо обрыва соединения
                print(f"сбой синтеза: {error!r}", flush=True)
                self._reply(500, b"", "text/plain")
                return
            print(f"синтез {time.perf_counter() - started:.3f} с", flush=True)
            self._reply(200, pcm, "application/octet-stream")

        def _reply(self, status: int, body: bytes, kind: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002 — имя из базового класса
            """Без журнала запросов: хватает времени синтеза, текст реплик не пишем."""

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", required=True, help="образец голоса, WAV")
    parser.add_argument("--ref-text", required=True, help="refs.json с текстом образцов")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--steps", type=int, default=32)
    parser.add_argument("--no-flash", dest="flash", action="store_false")
    args = parser.parse_args()
    voice = Voice(args)
    voice.warm_up()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(voice))
    print(f"готов: 127.0.0.1:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
