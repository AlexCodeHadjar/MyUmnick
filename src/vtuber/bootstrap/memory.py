"""Сборка памяти (Этап 10): LLM фонового слота, e5, хранилище, планировщик простоя, поиск в ходе.

Всё, что нужно памяти, живёт в одном контексте на время работы приложения. Недоступные части
не мешают диалогу: нет модели e5 или группы `memory` — задачи фактов падают в лог
(`MemoryUnavailable`), резюме истории (только LLM) работает, ход идёт без справки.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime

from vtuber.adapters.llm import LLMConfig
from vtuber.adapters.memory import E5Embedder, ObsidianVault, SqliteVecStore
from vtuber.application.memory import (
    ChatRecorder,
    FactExtractor,
    FactMemory,
    FactTransfer,
    MemoryControls,
    MemoryEditor,
    MemoryEraser,
    MemoryKeeper,
    MemoryParts,
    MemoryRecall,
    RecallSearch,
    Summarizer,
    TransferPaths,
    TransferRequests,
    VaultedFacts,
    VaultWatcher,
    reconcile,
)
from vtuber.application.scheduler import IdleJob, IdleScheduler
from vtuber.bootstrap.config import AppConfig, MemoryConfig
from vtuber.bootstrap.container import Conversation, Core, llm_backends
from vtuber.bootstrap.edition import language_pack
from vtuber.domain import MemoryUnavailable
from vtuber.kernel import get_logger
from vtuber.ports import EmbedderPort, GenerationParams, LLMPort, MemoryStorePort, MemoryVaultPort

_log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class _Engines:
    llm: LLMPort
    embedder: EmbedderPort
    store: MemoryStorePort
    vault: MemoryVaultPort


@dataclass(frozen=True, slots=True)
class SharedMemory:
    """Что общее у всех чатов (Этап 21): LLM фонового слота и e5 — грузятся один раз."""

    llm: LLMPort
    embedder: EmbedderPort


@asynccontextmanager
async def shared_memory(cfg: AppConfig) -> AsyncIterator[SharedMemory | None]:
    """Модели памяти на время работы приложения; память выключена — None."""
    if not cfg.memory.enabled:
        yield None
        return
    llm_cfg = _background_llm(cfg)
    async with (
        llm_backends().create(llm_cfg.backend, llm_cfg) as llm,
        E5Embedder(cfg.memory.e5) as embedder,
    ):
        yield SharedMemory(llm, embedder)


@asynccontextmanager
async def chat_memory(
    cfg: AppConfig, shared: SharedMemory, conversation: Conversation, core: Core
) -> AsyncIterator[MemoryControls]:
    """Память одного чата: своя база фактов, заметки, планировщик; история чата — в разговор.

    `cfg.memory` — с путями этого чата (`MemoryConfig.resolved`). Подписки — на `core.bus` чата:
    после переключения старые части событий не получают (ADR-0037).
    """
    memory = cfg.memory
    memory.store_path.parent.mkdir(parents=True, exist_ok=True)
    async with (
        SqliteVecStore(memory.store_path, memory.e5.dimensions) as store,
        asyncio.TaskGroup() as tg,
    ):
        vault = ObsidianVault(memory.vault_path)
        await _restore(vault, conversation, memory.restore_turns)
        engines = _Engines(shared.llm, shared.embedder, store, vault)
        scheduler, keeper = _wire(cfg, conversation, core, engines)
        loop = tg.create_task(scheduler.run())
        _log.info("memory.background_ready", store=str(memory.store_path))
        try:
            async with (
                _recording_chats(vault, core, tg) as recorder,
                _watching_notes(memory, engines, scheduler, core),
            ):
                yield MemoryControls(
                    MemoryEditor(vault, store, shared.embedder),
                    _eraser(engines, conversation, keeper, recorder),
                    lambda: scheduler.working,
                    _transfer(cfg, engines, scheduler),
                )
        finally:
            loop.cancel()


@asynccontextmanager
async def background_memory(
    cfg: AppConfig, conversation: Conversation, core: Core
) -> AsyncIterator[MemoryControls | None]:
    """Память одного чата вместе с моделями; выключена — пустой контекст (как до Этапа 21)."""
    async with shared_memory(cfg) as shared:
        if shared is None:
            yield None
            return
        async with chat_memory(cfg, shared, conversation, core) as controls:
            yield controls


@asynccontextmanager
async def _watching_notes(
    memory: MemoryConfig, engines: _Engines, scheduler: IdleScheduler, core: Core
) -> AsyncIterator[None]:
    watcher = VaultWatcher(
        engines.vault, scheduler.submit, lambda: _reconcile(engines), memory.vault_poll_s
    )
    watcher.follow(core.bus)
    watching = asyncio.create_task(watcher.run())
    try:
        yield
    finally:
        watching.cancel()
        await asyncio.wait({watching})


@asynccontextmanager
async def _recording_chats(
    vault: MemoryVaultPort, core: Core, tg: asyncio.TaskGroup
) -> AsyncIterator[ChatRecorder]:
    """На выходе очередь дописывается: последний ход перед закрытием не должен пропасть."""
    recorder = ChatRecorder(vault)
    recorder.follow(core.bus)
    recording = tg.create_task(recorder.run())
    try:
        yield recorder
    finally:
        recorder.stop()
        await recording


async def _restore(vault: MemoryVaultPort, conversation: Conversation, turns: int) -> None:
    """Папка недоступна — разговор начнётся с чистого листа: диалог важнее истории."""
    try:
        restored = await vault.recent_turns(turns)
        conversation.history.restore(restored, await vault.summary())
    except MemoryUnavailable as exc:
        _log.warning("memory.not_restored", problem=str(exc))


def _wire(
    cfg: AppConfig, conversation: Conversation, core: Core, engines: _Engines
) -> tuple[IdleScheduler, MemoryKeeper]:
    """Фон — подпиской на шину, поиск — подключением к сервису хода."""
    memory = cfg.memory
    params = GenerationParams(
        max_tokens=memory.generation.max_tokens, temperature=memory.generation.temperature
    )
    scheduler = IdleScheduler(cfg.scheduler)
    scheduler.follow(core.bus)
    texts = language_pack(cfg.edition.language).memory
    extractor = FactExtractor(engines.llm, params, texts)
    vaulted = VaultedFacts(engines.store, engines.vault)
    facts = FactMemory(extractor, engines.embedder, vaulted, memory.facts)
    summarizer = Summarizer(engines.llm, params, texts)
    keeper = MemoryKeeper(scheduler, conversation.history, summarizer, facts)
    keeper.on_summary = engines.vault.save_summary
    keeper.follow(core.bus)
    # В простое: e5 на CPU и другая работа по файлам не должны задерживать первую реплику.
    scheduler.submit(IdleJob("vault:reconcile", lambda: _reconcile(engines)))
    recall = MemoryRecall(
        RecallSearch(engines.embedder, engines.store), memory.retrieval, core.telemetry, texts
    )
    conversation.service.use_memory(recall.hints)
    return scheduler, keeper


def _eraser(
    engines: _Engines, conversation: Conversation, keeper: MemoryKeeper, recorder: ChatRecorder
) -> MemoryEraser:
    async def quiet() -> None:
        keeper.forget()
        await recorder.drain()

    return MemoryEraser(engines.vault, engines.store, conversation.history, quiet)


def _transfer(cfg: AppConfig, engines: _Engines, scheduler: IdleScheduler) -> TransferRequests:
    """Перенос фактов (S-20.10): переводит только русское ядро — его модель знает оба языка."""
    edition = cfg.edition
    own, other = edition.language, "ru" if edition.language == "en" else "en"
    paths = TransferPaths(cfg.memory.inbox, cfg.memory.transfer_to, own, other)
    generation = cfg.memory.generation
    params = GenerationParams(max_tokens=generation.max_tokens, temperature=generation.temperature)
    translator = (engines.llm, params) if own == "ru" else None
    memory = MemoryParts(engines.vault, engines.store, engines.embedder)
    requests = TransferRequests(FactTransfer(paths, memory, translator), scheduler)
    requests.import_on_start(datetime.now(UTC))
    return requests


async def _reconcile(engines: _Engines) -> None:
    await reconcile(engines.vault, engines.store, engines.embedder)


def _background_llm(cfg: AppConfig) -> LLMConfig:
    """Тот же сервер, другой слот: кэш диалога в слоте 0 фон не трогает."""
    slot = cfg.llm.llamacpp.model_copy(update={"slot_id": cfg.memory.background_slot_id})
    return cfg.llm.model_copy(update={"llamacpp": slot})
