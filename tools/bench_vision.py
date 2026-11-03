"""Цена картинки в ходе (S-18.1): TTFT реплики с картинкой и без неё на настоящем сервере.

Запуск: `uv run python -m tools.bench_vision [--runs 5] [--out отчёт.json]`. Сервер — из `[llm]`, с
`--mmproj`. Картинка каждый раз новая: иначе кэш промпта занизил бы цену. VRAM снимает скрипт.
"""

import argparse
import asyncio
import base64
import json
import os
import struct
import sys
import time
import zlib
from collections.abc import Mapping, Sequence
from contextlib import aclosing
from pathlib import Path
from typing import Final, TextIO

from tools.bench_latency import percentile
from tools.llm_client import open_llm
from vtuber.domain import AttachedImage, Message, Role, VisionUnavailable, VtuberError
from vtuber.ports import GenerationParams, LLMPort

SIDE: Final = 512
MS_PER_S: Final = 1000
P50: Final = 0.5
P95: Final = 0.95
EXIT_FAILED: Final = 1
_TEXT: Final = "Опиши одной фразой, что ты видишь."


def _chunk(kind: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(kind + data)
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)


def sample_image(seed: int, side: int = SIDE) -> AttachedImage:
    """PNG с разным узором на каждый `seed`: похожий размер, но кэш не поможет."""
    rows = b"".join(
        b"\x00" + bytes((x * (seed + 1) + y) % 256 for x in range(side) for _ in range(3))
        for y in range(side)
    )
    header = struct.pack(">IIBBBBB", side, side, 8, 2, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(rows))
        + _chunk(b"IEND", b"")
    )
    return AttachedImage("image/png", base64.b64encode(png).decode())


async def first_token_ms(llm: LLMPort, message: Message) -> float:
    """От запроса до первого токена; ответ дочитывается, чтобы слот освободился."""
    params = GenerationParams(max_tokens=32, temperature=0.2)
    started = time.perf_counter()
    first: float | None = None
    async with aclosing(llm.stream([message], params)) as deltas:
        async for _ in deltas:
            first = first if first is not None else time.perf_counter()
    return ((first or time.perf_counter()) - started) * MS_PER_S


async def measure(llm: LLMPort, runs: int) -> dict[str, list[float]]:
    """По очереди: с картинкой и без, чтобы прогрев не достался одной стороне."""
    image: list[float] = []
    text: list[float] = []
    for seed in range(runs):
        message = Message(Role.USER, f"{_TEXT} ({seed})", (sample_image(seed),))
        image.append(await first_token_ms(llm, message))
        text.append(await first_token_ms(llm, Message(Role.USER, f"{_TEXT} ({seed})")))
    return {"image_ttft_ms": image, "text_ttft_ms": text}


def summary(samples: Mapping[str, Sequence[float]]) -> dict[str, dict[str, float]]:
    """p50 и p95 каждой стороны."""
    return {
        name: {"p50": percentile(values, P50), "p95": percentile(values, P95)}
        for name, values in samples.items()
    }


async def _run(runs: int, env: Mapping[str, str]) -> dict[str, list[float]]:
    async with open_llm(None, env) as llm:
        return await measure(llm, runs)


def main(argv: Sequence[str], env: Mapping[str, str], out: TextIO) -> int:
    """Код возврата: 0 — готово, 1 — сервер без проектора или сбой."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        samples = asyncio.run(_run(args.runs, env))
    except (VisionUnavailable, VtuberError) as exc:
        print(f"Замер прерван: {exc}", file=out)
        return EXIT_FAILED
    text = json.dumps(summary(samples), ensure_ascii=False, indent=1)
    print(text, file=out)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:], os.environ, sys.stdout))
