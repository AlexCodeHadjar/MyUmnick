"""Телефон как MTP-устройство (S-24.7): `mtp.ps1` отдельным процессом с тайм-аутом."""

import asyncio
import tempfile
from pathlib import Path
from typing import Final, Protocol

_SCRIPT: Final = Path(__file__).with_name("mtp.ps1")
_TIMEOUT_S: Final = 30.0


class PhoneDrive(Protocol):
    """Папка обмена телефона; фейк для тестов — в `tests/plugins/test_phone_sync.py`."""

    async def find(self) -> str | None:
        """Имя подключённого телефона с папкой UmNick или `None`."""
        ...

    async def pull_notes(self) -> str | None:
        """Содержимое `notes.jsonl` телефона или `None`."""
        ...

    async def push_from_pc(self, payload: str) -> bool:
        """Положить `from_pc.jsonl`; `True` — получилось."""
        ...


class MtpDrive:
    """Через PowerShell и Shell.Application: Windows, без новых зависимостей (ADR-0050)."""

    async def find(self) -> str | None:
        """Имя телефона с папкой UmNick или `None`."""
        with tempfile.TemporaryDirectory() as temp:
            return await _run("find", Path(temp))

    async def pull_notes(self) -> str | None:
        """Скопировать `notes.jsonl` во временную папку и прочитать."""
        with tempfile.TemporaryDirectory() as temp:
            if await _run("pull", Path(temp)) is None:
                return None
            target = Path(temp) / "notes.jsonl"
            return await asyncio.to_thread(target.read_text, encoding="utf-8")

    async def push_from_pc(self, payload: str) -> bool:
        """Записать `from_pc.jsonl` локально и скопировать на телефон."""
        with tempfile.TemporaryDirectory() as temp:
            await asyncio.to_thread(
                (Path(temp) / "from_pc.jsonl").write_text, payload, encoding="utf-8"
            )
            return await _run("push", Path(temp)) is not None


async def _run(op: str, temp: Path) -> str | None:
    process = await asyncio.create_subprocess_exec(
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(_SCRIPT),
        op,
        str(temp),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        out, _ = await asyncio.wait_for(process.communicate(), _TIMEOUT_S)
    except TimeoutError:
        process.kill()
        await process.wait()
        return None
    if process.returncode != 0:
        return None
    return out.decode("utf-8", errors="replace").strip() or None
