"""Корень композиции: создание и связывание объектов приложения (ADR-0001)."""

from dataclasses import dataclass

from vtuber.adapters.llm import LlamaCppLLM, LLMConfig, OpenAICompatLLM
from vtuber.adapters.tts import PiperTTS, SileroTTS, TTSConfig
from vtuber.application.conversation import ConversationService
from vtuber.application.memory import ShortTermMemory
from vtuber.application.pipeline import ReplyPipeline, Voice
from vtuber.application.prompting import ContextBudget, PromptBuilder
from vtuber.bootstrap.config import AppConfig
from vtuber.domain import Persona
from vtuber.kernel import EventBus, Registry, Telemetry
from vtuber.ports import GenerationParams, LLMPort, TTSPort

type TTSAdapter = SileroTTS | PiperTTS
"""Движок TTS: порт и асинхронный контекстный менеджер (модель грузится в `async with`)."""


@dataclass(frozen=True, slots=True)
class Core:
    """Общие механизмы, которые получают все: шина событий и телеметрия."""

    bus: EventBus
    telemetry: Telemetry


@dataclass(frozen=True, slots=True)
class Backends:
    """Внешние движки хода: LLM обязательна, голос — только у шлюза (в терминале нет звука)."""

    llm: LLMPort
    tts: TTSPort | None


def llm_backends() -> Registry[LLMConfig, OpenAICompatLLM]:
    """Реестр LLM-адаптеров: имя из `[llm].backend` → адаптер (асинхронный контекстный менеджер).

    Новый адаптер — одна строка здесь (OCP); код вне адаптера не меняется.
    """
    backends = Registry[LLMConfig, OpenAICompatLLM]("llm-бэкенд")
    backends.add("llamacpp", LlamaCppLLM)
    backends.add("openai_compat", OpenAICompatLLM)
    return backends


def tts_backends() -> Registry[TTSConfig, TTSAdapter | None]:
    """Реестр движков TTS: имя из `[tts].backend` → адаптер; `none` — без голоса (OCP)."""
    backends = Registry[TTSConfig, TTSAdapter | None]("tts-движок")
    backends.add("silero", lambda cfg: SileroTTS(cfg.silero))
    backends.add("piper", lambda cfg: PiperTTS(cfg.piper))
    backends.add("none", lambda _: None)
    return backends


def build_conversation(
    cfg: AppConfig, persona: Persona, backends: Backends, core: Core
) -> tuple[ConversationService, PromptBuilder]:
    """Собирает сервис хода; `PromptBuilder` отдаётся и наружу — для прогрева кэша (T-06)."""
    generation = cfg.llm.generation
    params = GenerationParams(max_tokens=generation.max_tokens, temperature=generation.temperature)
    voice = None if backends.tts is None else Voice(backends.tts, cfg.pipeline.chunker)
    prompts = PromptBuilder(persona)
    service = ConversationService(
        ReplyPipeline(backends.llm, params, core.telemetry, voice),
        prompts,
        ShortTermMemory(ContextBudget(cfg.context)),
        core.bus,
    )
    return service, prompts
