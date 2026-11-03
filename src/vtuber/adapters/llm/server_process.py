"""llama-server как дочерний процесс ядра (ADR-0019): в поставке его запускает само приложение.

Флаги — те же, что в `scripts/start_llm.ps1` (T-03, T-08, T-10). Выключено по умолчанию: при
разработке сервер запускают отдельно, и он переживает перезапуски ядра.
"""

import asyncio
import subprocess
import time
from pathlib import Path
from types import TracebackType
from typing import Final, Self
from urllib.parse import urlsplit

import httpx
from pydantic import Field

from vtuber.domain import LLMUnavailable
from vtuber.kernel import ConfigSection, get_logger

HEALTH_PATH: Final = "/health"
HTTP_OK: Final = 200
POLL_S: Final = 0.2
# Без флага у приложения без консоли (sidecar Tauri) мигало бы окно.
_NO_WINDOW: Final = getattr(subprocess, "CREATE_NO_WINDOW", 0)

_log = get_logger(__name__)


class LlamaServerConfig(ConfigSection):
    """Секция `[llama_server]`: пути от корня проекта; `extra_args` — перед остальными флагами."""

    autostart: bool
    executable: Path
    model: Path
    log_file: Path
    context_size: int = Field(gt=0)
    slots: int = Field(gt=0)
    ready_timeout_s: float = Field(gt=0)
    stop_timeout_s: float = Field(gt=0)
    extra_args: tuple[str, ...]

    def resolved(self, root: Path) -> "LlamaServerConfig":
        """Копия с путями от корня проекта."""
        return self.model_copy(
            update={
                "executable": root / self.executable,
                "model": root / self.model,
                "log_file": root / self.log_file,
            }
        )


def server_arguments(cfg: LlamaServerConfig, base_url: str) -> list[str]:
    """Аргументы запуска; адрес берётся из `[llm].base_url`, чтобы они не разошлись."""
    address = urlsplit(base_url)
    return [
        *cfg.extra_args,
        "--model",
        str(cfg.model),
        "--n-gpu-layers",
        "99",
        "--ctx-size",
        str(cfg.context_size),
        "--parallel",
        str(cfg.slots),
        "--flash-attn",
        "on",
        "--jinja",
        "--reasoning-budget",
        "0",
        "--metrics",
        "--no-webui",
        "--host",
        address.hostname or "127.0.0.1",
        "--port",
        str(address.port or 8080),
    ]


class LlamaServerProcess:
    """Живёт столько же, сколько контекст; выключен в конфиге — ничего не делает."""

    def __init__(self, cfg: LlamaServerConfig, base_url: str) -> None:
        self._cfg = cfg
        self._base_url = base_url.rstrip("/")
        self._process: asyncio.subprocess.Process | None = None

    async def __aenter__(self) -> Self:
        if self._cfg.autostart:
            await self._start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        process = self._process
        if process is None or process.returncode is not None:
            return
        process.terminate()
        try:
            async with asyncio.timeout(self._cfg.stop_timeout_s):
                await process.wait()
        except TimeoutError:
            process.kill()
            await process.wait()

    async def wait_ready(self) -> None:
        """Ждёт, пока сервер загрузит модель.

        Raises:
            LLMUnavailable: сервер завершился или не успел за `ready_timeout_s`; текст — что делать.

        """
        if self._process is None:
            return
        deadline = time.monotonic() + self._cfg.ready_timeout_s
        async with httpx.AsyncClient(timeout=POLL_S * 5) as client:
            while time.monotonic() < deadline:
                if self._process.returncode is not None:
                    code = self._process.returncode
                    msg = f"llama-server завершился с кодом {code}: см. {self._cfg.log_file}"
                    raise LLMUnavailable(msg)
                if await _healthy(client, self._base_url + HEALTH_PATH):
                    return
                await asyncio.sleep(POLL_S)
        limit = self._cfg.ready_timeout_s
        msg = f"llama-server не загрузил модель за {limit} с: см. {self._cfg.log_file}"
        raise LLMUnavailable(msg)

    async def _start(self) -> None:
        cfg = self._cfg
        cfg.log_file.parent.mkdir(parents=True, exist_ok=True)
        with cfg.log_file.open("ab") as log:
            try:
                self._process = await asyncio.create_subprocess_exec(
                    str(cfg.executable),
                    *server_arguments(cfg, self._base_url),
                    stdout=log,
                    stderr=log,
                    stdin=asyncio.subprocess.DEVNULL,
                    creationflags=_NO_WINDOW,
                )
            except OSError as exc:
                # Диалога не будет, но окно и настройки должны открыться: статус LLM покажет сбой.
                _log.warning("llama_server.not_started", problem=str(exc))
                return
        _log.info("llama_server.started", pid=self._process.pid)


async def _healthy(client: httpx.AsyncClient, url: str) -> bool:
    try:
        return (await client.get(url)).status_code == HTTP_OK
    except httpx.HTTPError:
        return False
