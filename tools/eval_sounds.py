"""Точность меток звуков на записях (S-14.4): настоящая модель, настоящие файлы.

Запуск: `uv run python -m tools.eval_sounds папка [--window-s 3]`. Файлы — WAV, моно, 16 бит; что в
записи, говорит начало имени: `laughter_1.wav`, `cough-kitchen.wav`, `speech_ru.wav`. `speech` и
`none` значат, что реагировать не на что: это проверка ложных срабатываний.
"""

import argparse
import asyncio
import os
import sys
import time
import wave
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TextIO

from tools.llm_client import ROOT
from vtuber.adapters.stt.sensevoice import SenseVoiceSounds
from vtuber.bootstrap import load_app_config
from vtuber.domain import AudioChunk, AudioFormat, SoundKind, VtuberError

NOTHING: Final = "none"
PERCENT: Final = 100
EXIT_FAILED: Final = 1
_NOT_A_SOUND: Final = frozenset({"speech", NOTHING})


@dataclass(frozen=True, slots=True)
class Window:
    """Одно окно записи: что в нём должно быть и что услышала модель."""

    expected: str
    heard: str
    seconds: float


def label_of(path: Path) -> str | None:
    """Метка из начала имени файла; незнакомое начало — файл не из набора."""
    start = path.stem.replace("-", "_").split("_")[0].lower()
    known = {kind.value for kind in SoundKind} | _NOT_A_SOUND
    if start not in known:
        return None
    return NOTHING if start == "speech" else start


def render(windows: Sequence[Window]) -> str:
    """Для каждой метки: сколько окон услышано верно; затем ложные срабатывания и скорость."""
    totals = Counter(w.expected for w in windows)
    right = Counter(w.expected for w in windows if w.heard == w.expected)
    lines = [
        f"{label}: {right[label]}/{total} ({PERCENT * right[label] / total:.0f} %)"
        for label, total in sorted(totals.items())
    ]
    false_alarms = Counter(w.heard for w in windows if w.heard not in (w.expected, NOTHING))
    lines.append(f"лишние метки: {dict(false_alarms)}")
    if windows:
        lines.append(
            f"разбор окна: в среднем {sum(w.seconds for w in windows) / len(windows):.3f} с"
        )
    return "\n".join(lines)


def _chunks(path: Path, window_s: float) -> Iterable[AudioChunk]:
    with wave.open(str(path), "rb") as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2:  # noqa: PLR2004 — моно, 16 бит
            msg = f"{path.name}: нужен WAV, моно, 16 бит"
            raise VtuberError(msg)
        rate = wav.getframerate()
        while frames := wav.readframes(round(window_s * rate)):
            yield AudioChunk(AudioFormat(rate), frames)


async def _run(paths: Sequence[Path], window_s: float, env: Mapping[str, str]) -> list[Window]:
    cfg = load_app_config(ROOT, env).stt.resolved(ROOT)
    windows = []
    async with SenseVoiceSounds(cfg.sound_model) as sounds:
        for path in paths:
            if (expected := label_of(path)) is None:
                continue
            for chunk in _chunks(path, window_s):
                started = time.perf_counter()
                kind = await sounds.classify(chunk)
                heard = NOTHING if kind is None else kind.value
                windows.append(Window(expected, heard, time.perf_counter() - started))
    return windows


def main(argv: Sequence[str], env: Mapping[str, str], out: TextIO) -> int:
    """Код возврата: 0 — готово, 1 — нет модели или плохой файл."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--window-s", type=float, default=3.0)
    args = parser.parse_args(argv)
    try:
        windows = asyncio.run(_run(sorted(args.folder.glob("*.wav")), args.window_s, env))
    except VtuberError as exc:
        print(f"Оценка прервана: {exc}", file=out)
        return EXIT_FAILED
    print(render(windows), file=out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:], os.environ, sys.stdout))
