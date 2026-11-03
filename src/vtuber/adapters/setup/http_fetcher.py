"""Загрузка файлов мастера по HTTP с докачкой (S-13.2); модели лежат на разных хостингах."""

from collections.abc import AsyncGenerator
from typing import Final

import httpx

from vtuber.domain import SetupFailed
from vtuber.kernel import ConfigSection

_CHUNK: Final = 1024 * 1024
_PARTIAL_CONTENT: Final = 206
_RANGE_NOT_SATISFIABLE: Final = 416


class HttpFetcherConfig(ConfigSection):
    """Подсекция `[setup.http]`: тайм-ауты соединения и ожидания следующей порции (R-36)."""

    connect_timeout_s: float
    read_timeout_s: float


class HttpFetcher:
    """`FileFetcher`: сервер без поддержки Range отдаёт файл сначала, начало просто пропускается."""

    def __init__(self, cfg: HttpFetcherConfig) -> None:
        self._timeout = httpx.Timeout(
            connect=cfg.connect_timeout_s, read=cfg.read_timeout_s, write=None, pool=None
        )

    async def fetch(self, url: str, offset: int) -> AsyncGenerator[bytes]:
        """Байты файла с позиции `offset`."""
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        try:
            async with (
                httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client,
                client.stream("GET", url, headers=headers) as response,
            ):
                if response.status_code == _RANGE_NOT_SATISFIABLE:
                    return  # `.part` уже целиком: остаётся проверить сумму
                response.raise_for_status()
                skip = 0 if response.status_code == _PARTIAL_CONTENT else offset
                async for chunk in response.aiter_bytes(_CHUNK):
                    tail = chunk[skip:]
                    skip = max(0, skip - len(chunk))
                    if tail:
                        yield tail
        except httpx.HTTPError as exc:
            msg = f"Не удалось скачать файл: {exc}. Проверьте интернет и повторите"
            raise SetupFailed(msg) from exc
