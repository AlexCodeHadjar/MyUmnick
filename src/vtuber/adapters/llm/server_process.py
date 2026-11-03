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

from vtuber.adapters.llm.job_object import ChildBinding
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
    mmproj: Path | None = None  # проектор для картинок (ADR-0024); занимает видеопамять

    def resolved(self, root: Path) -> "LlamaServerConfig":
        """Копия с путями от корня проекта."""
        return self.model_copy(
            update={
                "executable": root / self.executable,
                "model": root / self.model,
                "log_file": root / self.log_file,
                "mmproj": None if self.mmproj is None else root / self.mmproj,
            }
        )


def server_arguments(cfg: LlamaServerConfig, base_url: str) -> list[str]:
    """Аргументы запуска; адрес берётся из `[llm].base_url`, чтобы они не разошлись."""
    address = urlsplit(base_url)
    return [
        *cfg.extra_args,
        *(() if cfg.mmproj is None else ("--mmproj", str(cfg.mmproj))),
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
        self._binding = ChildBinding()
        # Один клиент и без SSL (адрес — localhost): новый на проверку стоит 873 мс против 5 мс,
        # он грузит сертификаты и держит цикл событий, и здоровый сервер считался зависшим.
        self._client = httpx.AsyncClient(
            timeout=POLL_S * 5,
            verify=False,  # noqa: S501
            trust_env=False,
        )

    @property
    def started(self) -> bool:
        """Запущен ли сервер ядром: только такой наблюдатель может поднять заново."""
        return self._process is not None

    async def healthy(self) -> bool:
        """Процесс жив и отвечает; для наблюдателя (S-17.1)."""
        if self._process is None or self._process.returncode is not None:
            return False
        return await _healthy(self._client, self._base_url + HEALTH_PATH)

    async def restart(self) -> None:
        """Останавливает прежний процесс, даже зависший, и запускает новый; затем — `wait_ready`."""
        await self._stop()
        await self._start()

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
        await self._stop()
        await self._client.aclose()

    async def _stop(self) -> None:
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
        while time.monotonic() < deadline:
            if self._process.returncode is not None:
                code = self._process.returncode
                msg = f"llama-server завершился с кодом {code}: см. {self._cfg.log_file}"
                raise LLMUnavailable(msg)
            if await _healthy(self._client, self._base_url + HEALTH_PATH):
                return
            await asyncio.sleep(POLL_S)
        limit = self._cfg.ready_timeout_s
        msg = f"llama-server не загрузил модель за {limit} с: см. {self._cfg.log_file}"
        raise LLMUnavailable(msg)

    async def _start(self) -> None:
        cfg = self._cfg
        if not cfg.model.is_file():
            # Обычное состояние до мастера первого запуска: окно должно открыться и без модели.
            _log.info("llama_server.no_model", model=str(cfg.model))
            return
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
        self._binding.bind(self._process.pid)
        _log.info("llama_server.started", pid=self._process.pid)


async def _healthy(client: httpx.AsyncClient, url: str) -> bool:
    try:
        return (await client.get(url)).status_code == HTTP_OK
    except httpx.HTTPError:
        return False
