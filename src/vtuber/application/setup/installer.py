"""Установка компонентов (S-13.2): скачать, проверить сумму, положить на место атомарно.

Файл появляется под своим именем только после проверки: обрыв или подмена не оставят битую модель,
а докачка продолжит `.part` с места разрыва. Ничего не скачивается без явного вызова `install`,
а его UI делает только после согласия пользователя.
"""

import asyncio
import hashlib
import os
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Final

from vtuber.application.setup.catalog import CatalogFile, CatalogItem
from vtuber.domain import SetupFailed
from vtuber.kernel import get_logger
from vtuber.ports import FileFetcher

_CHUNK: Final = 1024 * 1024
_PART_SUFFIX: Final = ".part"
# Запас под рост логов и памяти: диск «в ноль» ломает всё приложение, а не только установку.
_FREE_DISK_RESERVE: Final = 1024**3

_log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class InstallProgress:
    """Сколько байт готово из общего числа, какой файл качается."""

    done: int
    total: int
    file: str


type ProgressSink = Callable[[InstallProgress], Awaitable[None]]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def _is_valid_size(path: Path, size: int) -> bool:
    return path.is_file() and path.stat().st_size == size


def _append(out: BinaryIO, chunk: bytes) -> None:
    out.write(chunk)


class Installer:
    """Ставит компоненты каталога в корень приложения; пути не выходят за пределы корня."""

    def __init__(self, root: Path, fetcher: FileFetcher, free_disk: Callable[[Path], int]) -> None:
        self._root = root
        self._fetcher = fetcher
        self._free_disk = free_disk

    def is_installed(self, item: CatalogItem) -> bool:
        """Все файлы на месте нужного размера; сумма проверялась при установке."""
        return all(_is_valid_size(self._target(file), file.size) for file in item.files)

    async def install(self, items: Sequence[CatalogItem], progress: ProgressSink) -> None:
        """Скачивает недостающее.

        Raises:
            SetupFailed: нет места, сеть недоступна или сумма не совпала; текст — что делать.

        """
        files = [file for item in items for file in item.files]
        missing = [file for file in files if not _is_valid_size(self._target(file), file.size)]
        self._check_disk(missing)
        total = sum(file.size for file in files)
        done = total - sum(file.size for file in missing)
        for file in missing:
            done = await self._install_file(file, (done, total), progress)
        await progress(InstallProgress(total, total, ""))

    def _target(self, file: CatalogFile) -> Path:
        target = (self._root / file.path).resolve()
        if not target.is_relative_to(self._root.resolve()):
            msg = f"Каталог ведёт за пределы приложения: {file.path}"
            raise SetupFailed(msg)
        return target

    def _check_disk(self, files: Sequence[CatalogFile]) -> None:
        need = sum(file.size for file in files) + _FREE_DISK_RESERVE
        self._root.mkdir(parents=True, exist_ok=True)
        free = self._free_disk(self._root)
        if free < need:
            gb = 1024**3
            msg = f"Не хватает места на диске: нужно {need // gb} ГБ, свободно {free // gb} ГБ"
            raise SetupFailed(msg)

    async def _install_file(
        self, file: CatalogFile, counters: tuple[int, int], progress: ProgressSink
    ) -> int:
        done, total = counters
        target = self._target(file)
        part = target.with_name(target.name + _PART_SUFFIX)
        target.parent.mkdir(parents=True, exist_ok=True)
        offset = part.stat().st_size if part.is_file() else 0
        offset = 0 if offset > file.size else offset
        with part.open("ab" if offset else "wb") as out:
            done += offset
            async for chunk in self._fetcher.fetch(file.url, offset):
                await asyncio.to_thread(_append, out, chunk)
                done += len(chunk)
                await progress(InstallProgress(done, total, file.path))
        await self._verify_and_place(file, part, target)
        _log.info("setup.file_installed", file=file.path)
        return done

    async def _verify_and_place(self, file: CatalogFile, part: Path, target: Path) -> None:
        actual = await asyncio.to_thread(_sha256, part)
        if actual != file.sha256:
            await asyncio.to_thread(part.unlink)
            msg = f"Файл {file.path} пришёл повреждённым (сумма не совпала): повторите загрузку"
            raise SetupFailed(msg)
        await asyncio.to_thread(os.replace, part, target)
