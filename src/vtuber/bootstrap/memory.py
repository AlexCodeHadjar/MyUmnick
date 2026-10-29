"""Сборка фоновой памяти (Этап 10): LLM фонового слота, e5, хранилище, планировщик простоя.

Всё, что нужно памяти, живёт в одном контексте на время работы приложения. Недоступные части
не мешают диалогу: нет модели e5 или группы `memory` — задачи фактов падают в лог
(`MemoryUnavailable`), резюме истории (только LLM) работает.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from vtuber.adapters.memory import E5Embedder, SqliteVecStore
from vtuber.application.memory import (
    FactExtractor,
    FactMemory,
    MemoryKeeper,
    ShortTermMemory,
    Summarizer,
)
from vtuber.application.scheduler import IdleScheduler
from vtuber.bootstrap.config import AppConfig
from vtuber.bootstrap.container import llm_backends
from vtuber.kernel import EventBus, get_logger
from vtuber.ports import GenerationParams

_log = get_logger(__name__)


@asynccontextmanager
async def background_memory(
    cfg: AppConfig, history: ShortTermMemory, bus: EventBus
) -> AsyncIterator[None]:
    """Фоновая память на время контекста; выключена в конфиге — пустой контекст.

    `cfg.memory` — с путями от корня (`MemoryConfig.resolved`).
    """
    memory = cfg.memory
    if not memory.enabled:
        yield
        return
    slot = cfg.llm.llamacpp.model_copy(update={"slot_id": memory.background_slot_id})
    llm_cfg = cfg.llm.model_copy(update={"llamacpp": slot})
    memory.store_path.parent.mkdir(parents=True, exist_ok=True)
    params = GenerationParams(
        max_tokens=memory.generation.max_tokens, temperature=memory.generation.temperature
    )
    async with (
        llm_backends().create(llm_cfg.backend, llm_cfg) as llm,
        E5Embedder(memory.e5) as embedder,
        SqliteVecStore(memory.store_path, memory.e5.dimensions) as store,
        asyncio.TaskGroup() as tg,
    ):
        scheduler = IdleScheduler(cfg.scheduler)
        scheduler.follow(bus)
        facts = FactMemory(FactExtractor(llm, params), embedder, store, memory.facts)
        MemoryKeeper(scheduler, history, Summarizer(llm, params), facts).follow(bus)
        loop = tg.create_task(scheduler.run())
        _log.info("memory.background_ready", store=str(memory.store_path))
        try:
            yield
        finally:
            loop.cancel()
