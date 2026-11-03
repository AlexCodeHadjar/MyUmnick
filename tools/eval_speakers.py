"""Доля ошибок разделения собеседников на записях (S-14.3): настоящая модель, настоящие файлы.

Запуск: `uv run python -m tools.eval_speakers папка`. Файлы — WAV, моно, 16 бит, по одной фразе, в
порядке разговора: `01_anna.wav`, `02_boris.wav`. Говорящий — слово после номера. Считается по
разметке трекера: каждому номеру сопоставляется человек, которого он чаще слышал; остальное —
ошибки.
"""

import argparse
import asyncio
import os
import sys
import wave
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TextIO

from tools.llm_client import ROOT
from vtuber.adapters.stt.speaker_embedding import SherpaSpeakerEmbedder
from vtuber.application.voice import SpeakerTracker
from vtuber.bootstrap import load_app_config
from vtuber.domain import AudioChunk, AudioFormat, VtuberError

PERCENT: Final = 100
EXIT_FAILED: Final = 1
_PARTS_WITH_NUMBER: Final = 2


@dataclass(frozen=True, slots=True)
class Heard:
    """Фраза: кто говорил на самом деле и какой номер дал трекер."""

    person: str
    number: int


def person_of(path: Path) -> str | None:
    """Говорящий из имени файла `01_anna.wav`."""
    parts = path.stem.split("_", 1)
    return parts[1].lower() if len(parts) == _PARTS_WITH_NUMBER else None


def error_rate(heard: Sequence[Heard]) -> float:
    """Доля фраз, где номер не совпал с основным человеком этого номера."""
    by_number: dict[int, Counter[str]] = defaultdict(Counter)
    for item in heard:
        by_number[item.number][item.person] += 1
    right = sum(people.most_common(1)[0][1] for people in by_number.values())
    return 1 - right / len(heard) if heard else 0.0


def render(heard: Sequence[Heard]) -> str:
    """Итог: сколько голосов насчитано и доля ошибок."""
    people = len({item.person for item in heard})
    numbers = len({item.number for item in heard})
    return (
        f"Фраз: {len(heard)}; людей: {people}; голосов насчитано: {numbers}; "
        f"ошибок: {PERCENT * error_rate(heard):.0f} %"
    )


def _read(path: Path) -> AudioChunk:
    with wave.open(str(path), "rb") as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2:  # noqa: PLR2004 — моно, 16 бит
            msg = f"{path.name}: нужен WAV, моно, 16 бит"
            raise VtuberError(msg)
        return AudioChunk(AudioFormat(wav.getframerate()), wav.readframes(wav.getnframes()))


async def _run(paths: Sequence[Path], env: Mapping[str, str]) -> list[Heard]:
    stt = load_app_config(ROOT, env).stt.resolved(ROOT)
    embedder = SherpaSpeakerEmbedder(stt.speaker_model)
    tracker = SpeakerTracker(stt.speakers.threshold, stt.speakers.max_speakers)
    heard = []
    for path in paths:
        if (person := person_of(path)) is not None:
            vector = await embedder.embed(_read(path))
            heard.append(Heard(person, tracker.identify(vector)))
    return heard


def main(argv: Sequence[str], env: Mapping[str, str], out: TextIO) -> int:
    """Код возврата: 0 — готово, 1 — нет модели или плохой файл."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args(argv)
    try:
        heard = asyncio.run(_run(sorted(args.folder.glob("*.wav")), env))
    except VtuberError as exc:
        print(f"Оценка прервана: {exc}", file=out)
        return EXIT_FAILED
    print(render(heard), file=out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:], os.environ, sys.stdout))
