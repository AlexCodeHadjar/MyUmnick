"""Опрос видеопамяти через `nvidia-smi` (ADR-0018): идёт с драйвером, новой зависимости нет."""

import asyncio
import subprocess
from typing import Final

from vtuber.domain import GpuMemory
from vtuber.kernel import ConfigSection, get_logger

_COMMAND: Final = (
    "nvidia-smi",
    "--query-gpu=memory.total,memory.used",
    "--format=csv,noheader,nounits",
)
_FIELDS: Final = 2
# Без флага у приложения без консоли (sidecar Tauri) каждый опрос мигал бы окном.
_NO_WINDOW: Final = getattr(subprocess, "CREATE_NO_WINDOW", 0)

_log = get_logger(__name__)


class NvidiaSmiConfig(ConfigSection):
    """Подсекция опроса: срок одного вызова."""

    timeout_s: float


def parse_memory(output: str) -> GpuMemory | None:
    """Первая видеокарта из вывода `nvidia-smi`; непонятный вывод — None."""
    line = output.strip().splitlines()[0] if output.strip() else ""
    parts = [part.strip() for part in line.split(",")]
    if len(parts) != _FIELDS or not all(part.isdigit() for part in parts):
        return None
    return GpuMemory(total_mb=int(parts[0]), used_mb=int(parts[1]))


class NvidiaSmiProbe:
    """`GpuProbe`: None, если утилиты нет, карта не NVIDIA или вызов не уложился в срок."""

    def __init__(self, cfg: NvidiaSmiConfig) -> None:
        self._cfg = cfg

    async def memory(self) -> GpuMemory | None:
        """Текущая занятость видеопамяти."""
        try:
            process = await asyncio.create_subprocess_exec(
                *_COMMAND,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                creationflags=_NO_WINDOW,
            )
        except OSError as exc:
            _log.info("gpu.probe_unavailable", problem=str(exc))
            return None
        try:
            async with asyncio.timeout(self._cfg.timeout_s):
                output, _ = await process.communicate()
        except TimeoutError:
            process.kill()
            await process.wait()
            _log.warning("gpu.probe_timeout")
            return None
        return parse_memory(output.decode(errors="replace"))
