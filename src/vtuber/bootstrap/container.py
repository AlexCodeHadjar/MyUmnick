"""Корень композиции: создание и связывание объектов приложения (ADR-0001)."""

from dataclasses import dataclass

from vtuber.adapters.llm import LlamaCppLLM, LLMConfig, OpenAICompatLLM
from vtuber.application.conversation import ConversationService
from vtuber.application.memory import ShortTermMemory
from vtuber.application.pipeline import ReplyPipeline
from vtuber.application.prompting import ContextBudget, PromptBuilder
from vtuber.bootstrap.config import AppConfig
from vtuber.domain import Persona
from vtuber.kernel import EventBus, Registry, Telemetry
from vtuber.ports import GenerationParams, LLMPort


@dataclass(frozen=True, slots=True)
class Core:
    """Общие механизмы, которые получают все: шина событий и телеметрия."""

    bus: EventBus
    telemetry: Telemetry


def llm_backends() -> Registry[LLMConfig, OpenAICompatLLM]:
    """Реестр LLM-адаптеров: имя из `[llm].backend` → адаптер (асинхронный контекстный менеджер).

    Новый адаптер — одна строка здесь (OCP); код вне адаптера не меняется.
    """
    backends = Registry[LLMConfig, OpenAICompatLLM]("llm-бэкенд")
    backends.add("llamacpp", LlamaCppLLM)
    backends.add("openai_compat", OpenAICompatLLM)
    return backends


def build_conversation(
    cfg: AppConfig, persona: Persona, llm: LLMPort, core: Core
) -> tuple[ConversationService, PromptBuilder]:
    """Собирает сервис хода; `PromptBuilder` отдаётся и наружу — для прогрева кэша (T-06)."""
    generation = cfg.llm.generation
    params = GenerationParams(max_tokens=generation.max_tokens, temperature=generation.temperature)
    prompts = PromptBuilder(persona)
    service = ConversationService(
        ReplyPipeline(llm, params, core.telemetry),
        prompts,
        ShortTermMemory(ContextBudget(cfg.context)),
        core.bus,
    )
    return service, prompts
