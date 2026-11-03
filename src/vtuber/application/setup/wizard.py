"""Сценарий мастера: состояние для UI, установка выбранного, запись выбора в `config/setup.toml`."""

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from vtuber.application.setup.catalog import CatalogItem, Recommendation, SetupCatalog, recommend
from vtuber.application.setup.installer import Installer, ProgressSink
from vtuber.domain import GpuMemory, SetupFailed
from vtuber.kernel import get_logger
from vtuber.ports import GpuProbe

type ChoiceWriter = Callable[[Mapping[str, Mapping[str, str | bool]]], None]
"""Записывает секции конфига, которыми владеет мастер; остальное остаётся за пользователем."""

_log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SetupState:
    """Что показать: нужен ли мастер, что на машине, что посоветовано и что уже стоит."""

    needed: bool
    gpu: GpuMemory | None
    recommendation: Recommendation
    installed: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SetupChoice:
    """Что выбрал пользователь в мастере."""

    item_ids: tuple[str, ...]
    voice: str


class SetupWizard:
    """Ставит только то, что выбрал пользователь; повторный вызов продолжает с места разрыва."""

    def __init__(
        self,
        catalog: SetupCatalog,
        installer: Installer,
        probe: GpuProbe,
        write_choice: ChoiceWriter,
    ) -> None:
        self._catalog = catalog
        self._installer = installer
        self._probe = probe
        self._write_choice = write_choice
        self._running: asyncio.Task[None] | None = None

    @property
    def catalog(self) -> SetupCatalog:
        """Каталог компонентов: его показывает UI."""
        return self._catalog

    @property
    def is_running(self) -> bool:
        """Идёт ли установка."""
        return self._running is not None and not self._running.done()

    async def state(self) -> SetupState:
        """Текущее состояние; мастер нужен, пока не стоит обязательное."""
        gpu = await self._probe.memory()
        installed = tuple(
            item.id for item in self._catalog.items if self._installer.is_installed(item)
        )
        needed = any(item.required and item.id not in installed for item in self._catalog.items)
        return SetupState(needed, gpu, recommend(self._catalog, gpu), installed)

    def start(
        self,
        choice: SetupChoice,
        progress: ProgressSink,
        finished: Callable[[str | None], Awaitable[None]],
    ) -> None:
        """Начинает установку в фоне; `finished(None)` — успех, иначе текст проблемы.

        Raises:
            SetupFailed: установка уже идёт, неизвестный компонент или голос, либо не выбрано
                обязательное.

        """
        if self.is_running:
            msg = "Установка уже идёт"
            raise SetupFailed(msg)
        items = self._resolve(choice)
        self._running = asyncio.create_task(self._run(items, choice.voice, progress, finished))

    def cancel(self) -> None:
        """Прервать загрузку; скачанное остаётся и продолжится при следующей попытке."""
        if self._running is not None:
            self._running.cancel()

    def _resolve(self, choice: SetupChoice) -> list[CatalogItem]:
        by_id = {item.id: item for item in self._catalog.items}
        unknown = [item_id for item_id in choice.item_ids if item_id not in by_id]
        if unknown or choice.voice not in self._catalog.voices:
            msg = f"Неизвестный выбор в мастере: {unknown or choice.voice}"
            raise SetupFailed(msg)
        absent = [
            i.title for i in self._catalog.items if i.required and i.id not in choice.item_ids
        ]
        if absent:
            msg = f"Без этого диалог не заработает: {', '.join(absent)}"
            raise SetupFailed(msg)
        return [by_id[item_id] for item_id in choice.item_ids]

    async def _run(
        self,
        items: list[CatalogItem],
        voice: str,
        progress: ProgressSink,
        finished: Callable[[str | None], Awaitable[None]],
    ) -> None:
        try:
            await self._installer.install(items, progress)
            await asyncio.to_thread(self._write_choice, self._sections(voice))
        except SetupFailed as exc:
            _log.warning("setup.failed", problem=str(exc))
            await finished(str(exc))
        else:
            _log.info("setup.finished")
            await finished(None)

    def _sections(self, voice: str) -> Mapping[str, Mapping[str, str | bool]]:
        return {
            "setup": {"enabled": True},
            "llama_server": {"autostart": True, "model": self._catalog.llm_model_path},
            "tts.silero": {"speaker": voice},
        }
