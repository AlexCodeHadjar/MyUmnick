"""Сборка памяти (Этап 10): LLM фонового слота, e5, хранилище, планировщик простоя, поиск в ходе.

Всё, что нужно памяти, живёт в одном контексте на время работы приложения. Недоступные части
не мешают диалогу: нет модели e5 или группы `memory` — задачи фактов падают в лог
(`MemoryUnavailable`), резюме истории (только LLM) работает, ход идёт без справки.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from vtuber.adapters.llm import LLMConfig
from vtuber.adapters.memory import E5Embedder, SqliteVecStore
from vtuber.application.memory import (
    FactExtractor,
    FactMemory,
    MemoryKeeper,
    MemoryRecall,
    Summarizer,
)
from vtuber.application.scheduler import IdleScheduler
from vtuber.bootstrap.config import AppConfig
from vtuber.bootstrap.container import Conversation, Core, llm_backends
from vtuber.kernel import get_logger
from vtuber.ports import EmbedderPort, GenerationParams, LLMPort, MemoryStorePort

_log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class _Engines:
    llm: LLMPort
    embedder: EmbedderPort
    store: MemoryStorePort


@asynccontextmanager
async def background_memory(
    cfg: AppConfig, conversation: Conversation, core: Core
) -> AsyncIterator[None]:
    """Память на время контекста: фон в простое и факты в ходе; выключена — пустой контекст.

    `cfg.memory` — с путями от корня (`MemoryConfig.resolved`).
    """
    memory = cfg.memory
    if not memory.enabled:
        yield
        return
    llm_cfg = _background_llm(cfg)
    memory.store_path.parent.mkdir(parents=True, exist_ok=True)
    async with (
        llm_backends().create(llm_cfg.backend, llm_cfg) as llm,
        E5Embedder(memory.e5) as embedder,
        SqliteVecStore(memory.store_path, memory.e5.dimensions) as store,
        asyncio.TaskGroup() as tg,
    ):
        scheduler = _wire(cfg, conversation, core, _Engines(llm, embedder, store))
        loop = tg.create_task(scheduler.run())
        _log.info("memory.background_ready", store=str(memory.store_path))
        try:
            yield
        finally:
            loop.cancel()


def _wire(
    cfg: AppConfig, conversation: Conversation, core: Core, engines: _Engines
) -> IdleScheduler:
    """Фон — подпиской на шину, поиск — подключением к сервису хода."""
    memory = cfg.memory
    params = GenerationParams(
        max_tokens=memory.generation.max_tokens, temperature=memory.generation.temperature
    )
    scheduler = IdleScheduler(cfg.scheduler)
    scheduler.follow(core.bus)
    extractor = FactExtractor(engines.llm, params)
    facts = FactMemory(extractor, engines.embedder, engines.store, memory.facts)
    summarizer = Summarizer(engines.llm, params)
    MemoryKeeper(scheduler, conversation.history, summarizer, facts).follow(core.bus)
    recall = MemoryRecall(engines.embedder, engines.store, memory.retrieval, core.telemetry)
    conversation.service.use_memory(recall.hints)
    return scheduler


def _background_llm(cfg: AppConfig) -> LLMConfig:
    """Тот же сервер, другой слот: кэш диалога в слоте 0 фон не трогает."""
    slot = cfg.llm.llamacpp.model_copy(update={"slot_id": cfg.memory.background_slot_id})
    return cfg.llm.model_copy(update={"llamacpp": slot})
