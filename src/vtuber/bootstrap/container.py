"""Корень композиции: создание и связывание объектов приложения (ADR-0001)."""

from dataclasses import dataclass

from vtuber.adapters.llm import LlamaCppLLM, LLMConfig, OpenAICompatLLM
from vtuber.adapters.tts import (
    FallbackTTS,
    KokoroTTS,
    PiperTTS,
    SileroTTS,
    TTSConfig,
    VoiceServerTTS,
)
from vtuber.application.conversation import ConversationService
from vtuber.application.memory import ShortTermMemory
from vtuber.application.pipeline import FillerBank, ReplyPipeline, Voice
from vtuber.application.prompting import ContextBudget, FloorGuard, PromptBuilder
from vtuber.bootstrap.config import AppConfig
from vtuber.bootstrap.edition import language_pack
from vtuber.domain import Persona
from vtuber.kernel import EventBus, Registry, Telemetry
from vtuber.ports import GenerationParams, LLMPort, TTSPort

type TTSAdapter = SileroTTS | PiperTTS | KokoroTTS | FallbackTTS
"""Движок TTS: порт и асинхронный контекстный менеджер (модель грузится в `async with`)."""


@dataclass(frozen=True, slots=True)
class Core:
    """Общие механизмы, которые получают все: шина событий и телеметрия."""

    bus: EventBus
    telemetry: Telemetry


@dataclass(frozen=True, slots=True)
class Backends:
    """Внешние движки хода: LLM обязательна, голос — только у шлюза (в терминале нет звука).

    `fillers` — междометия голоса; наполняются при загрузке модели голоса (T-17).
    """

    llm: LLMPort
    tts: TTSPort | None
    fillers: FillerBank | None = None


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
    backends.add("kokoro", lambda cfg: KokoroTTS(cfg.kokoro))
    backends.add(
        "voice_server",
        lambda cfg: FallbackTTS(VoiceServerTTS(cfg.voice_server), SileroTTS(cfg.silero)),
    )
    backends.add("none", lambda _: None)
    return backends


@dataclass(frozen=True, slots=True)
class Conversation:
    """Собранный диалог: сервис хода, сборщик промпта (прогрев, T-06), история (фоновая память)."""

    service: ConversationService
    prompts: PromptBuilder
    history: ShortTermMemory


def build_conversation(
    cfg: AppConfig, persona: Persona, backends: Backends, core: Core
) -> Conversation:
    """Собирает сервис хода; сборщик промпта и история отдаются наружу — прогреву и памяти."""
    generation = cfg.llm.generation
    params = GenerationParams(max_tokens=generation.max_tokens, temperature=generation.temperature)
    pack = language_pack(cfg.edition.language)
    voice = (
        None
        if backends.tts is None
        else Voice(
            backends.tts, cfg.pipeline.chunker, backends.fillers, core.bus.publish, pack.diction
        )
    )
    prompts = PromptBuilder(persona, pack.prompt)
    guarded = FloorGuard(backends.llm, pack.prompt.profile.refusal)  # жёсткий минимум (ADR-0033)
    history = ShortTermMemory(ContextBudget(cfg.context), pack.memory.summary_template)
    service = ConversationService(
        ReplyPipeline(guarded, params, core.telemetry, voice), prompts, history, core.bus
    )
    return Conversation(service, prompts, history)
