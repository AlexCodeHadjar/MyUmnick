"""Плагин пения (S-18.5, ADR-0028): персонаж исполняет готовую запись по команде ведущего.

Запись рендерит сам пользователь любым движком: здесь только показ, вне горячего пути. Рот двигается
сам, потому что UI считает его по звучащему сигналу, а отмена работает как у обычного ответа.
"""

import array
import asyncio
import time
import wave
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from pydantic import Field

from vtuber.domain import AudioChunk, AudioFormat, GenerationFailed
from vtuber.kernel import ConfigSection, PluginContext

_SAMPLE_WIDTH: Final = 2
_STEREO: Final = 2
_MS_PER_S: Final = 1000


class SingingConfig(ConfigSection):
    """Секция `[plugins.settings.singing]`: откуда брать записи и сколько звука держать впереди."""

    songs_dir: Path = Path("data/songs")
    lead_s: float = Field(default=2.0, gt=0)
    chunk_ms: int = Field(default=200, gt=0)


@dataclass(frozen=True, slots=True)
class _Pace:
    """Часы подачи; в тестах — подмена."""

    now: Callable[[], float] = time.monotonic
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep


def is_playable(path: Path) -> bool:
    """WAV, 16 бит, моно или стерео; о другом лучше сказать при старте, чем посреди песни."""
    try:
        with wave.open(str(path), "rb") as song:
            return song.getsampwidth() == _SAMPLE_WIDTH and song.getnchannels() <= _STEREO
    except (OSError, EOFError, wave.Error):
        return False


def to_mono(frames: bytes, channels: int) -> bytes:
    """Плеер принимает один канал."""
    if channels != _STEREO:
        return frames
    samples = array.array("h", frames)
    mono = array.array(
        "h", (samples[i] // 2 + samples[i + 1] // 2 for i in range(0, len(samples) - 1, 2))
    )
    return mono.tobytes()


async def song_chunks(
    path: Path,
    cfg: SingingConfig,
    pace: _Pace = _Pace(),  # noqa: B008 — неизменяемый объект
) -> AsyncGenerator[AudioChunk]:
    """Звук песни не быстрее, чем с запасом `lead_s`: иначе вся песня лежала бы в памяти плеера."""
    started = pace.now()
    sent_s = 0.0
    try:
        with wave.open(str(path), "rb") as song:
            audio_format = AudioFormat(song.getframerate())
            step = max(1, round(cfg.chunk_ms * song.getframerate() / _MS_PER_S))
            channels = song.getnchannels()
            while frames := await asyncio.to_thread(song.readframes, step):
                chunk = AudioChunk(audio_format, to_mono(frames, channels))
                yield chunk
                sent_s += chunk.duration_s
                ahead = sent_s - (pace.now() - started) - cfg.lead_s
                if ahead > 0:
                    await pace.sleep(ahead)
    except (OSError, EOFError, wave.Error) as exc:
        msg = f"Не получилось прочитать запись «{path.stem}»"
        raise GenerationFailed(msg) from exc


class SingingPlugin:
    """На каждую запись из папки — команда «спой <имя файла>»; зрителям команды недоступны."""

    name = "singing"

    async def setup(self, ctx: PluginContext) -> None:
        """Записи читаются при старте: новая песня — перезапуск."""
        cfg = ctx.settings(SingingConfig)
        for path in sorted(cfg.songs_dir.glob("*.wav")):
            if not is_playable(path):
                ctx.log.warning("singing.bad_file", file=path.name)
                continue
            title = path.stem.lower()

            async def sing(title: str = title, path: Path = path) -> None:
                await ctx.perform(title, song_chunks(path, cfg))

            ctx.add_command(f"спой {title}", sing)
            ctx.add_command(f"Спой {title}", sing)

    async def shutdown(self) -> None:
        """Держать нечего: файл открыт, только пока идёт песня."""
