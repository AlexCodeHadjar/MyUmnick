"""Порт загрузки файлов для мастера первого запуска (S-13.2)."""

from collections.abc import AsyncGenerator
from typing import Protocol


class FileFetcher(Protocol):
    """Откуда мастер берёт файлы; сбой — `SetupFailed` с понятным текстом."""

    def fetch(self, url: str, offset: int) -> AsyncGenerator[bytes]:
        """Байты файла, начиная с позиции `offset`."""
        ...
