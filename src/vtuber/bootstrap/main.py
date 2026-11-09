"""Точка входа: `python -m vtuber` — чат в терминале (M1), `python -m vtuber serve` — шлюз UI."""

import argparse
import asyncio
import os
import sys
from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import ExitStack, aclosing, asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol, TextIO

from vtuber.adapters.gpu import NvidiaSmiProbe
from vtuber.adapters.llm import LlamaServerProcess
from vtuber.application.conversation import ConversationService, Initiative
from vtuber.application.prompting import RU_PROMPT, PromptBuilder
from vtuber.application.scheduler import ResourceManager
from vtuber.application.supervision import Supervised, Supervisor
from vtuber.application.tools import ToolContext
from vtuber.bootstrap.config import AppConfig, load_app_config
from vtuber.bootstrap.container import Core, build_conversation, llm_backends
from vtuber.bootstrap.edition import edition_files, ignored_user_keys, resolve_edition
from vtuber.bootstrap.memory import background_memory
from vtuber.bootstrap.persona import load_persona
from vtuber.bootstrap.plugins import PluginServices, ResourceModels, running_plugins
from vtuber.bootstrap.supervision import (
    LlmSupervised,
    TtsSupervised,
    VoiceParts,
    build_voice,
    with_voice,
)
from vtuber.bootstrap.voice_input import voice_input
from vtuber.bootstrap.wiring import AppParts, connect_initiative, connect_panels
from vtuber.domain import (
    BackendState,
    BackendStatusChanged,
    Component,
    ConfigError,
    GenerationFailed,
    LLMUnavailable,
    Message,
    MetricRecorded,
    Persona,
    Role,
    TTSUnavailable,
)
from vtuber.gateway import (
    ExternalTurns,
    GatewayServer,
    TerminalChat,
)
from vtuber.kernel import EventBus, Telemetry, TraceWriter, get_logger, logging_to
from vtuber.ports import LLMPort

EXIT_CONFIG: Final = 1
EXIT_UNAVAILABLE: Final = 2
CHAT_MODE: Final = "chat"
SERVE_MODE: Final = "serve"
# Реплика прогрева кэша и проба голоса — в тексте издания (`PromptTexts`): шаблоны чата (Qwen3.5)
# отвергают промпт без реплики пользователя, а общий префикс от неё не меняется (T-06).
WARMUP_USER: Final = RU_PROMPT.warmup_user  # прежнее имя: русское издание
TTS_PROBE: Final = RU_PROMPT.tts_probe

_log = get_logger(__name__)


class LineSource(Protocol):
    """Откуда читать строки: `sys.stdin` или его тестовая замена."""

    def readline(self) -> str:
        """Следующая строка с переводом строки; пустая — конец ввода."""


class Console:
    """Ввод построчно в отдельном потоке — ожидание строки не блокирует цикл (R-34)."""

    def __init__(self, stdin: LineSource, out: TextIO) -> None:
        self._stdin = stdin
        self.out = out

    async def read_line(self) -> str | None:
        """Следующая строка или None в конце ввода."""
        line = await asyncio.to_thread(self._stdin.readline)
        return line or None


def main(argv: Sequence[str], env: Mapping[str, str], console: Console) -> int:
    """Код возврата: 0 — штатный выход, 1 — ошибка конфига, 2 — LLM недоступна (чат).

    Файлы логов и трасс открываются здесь, вне цикла событий, и живут до выхода.
    """
    args = _parse(argv)
    try:
        edition = resolve_edition(args.edition, env)
        cfg = load_app_config(args.root, env, edition)
        resolved = {
            "tts": cfg.tts.resolved(args.root),
            "memory": cfg.memory.resolved(args.root),
            "stt": cfg.stt.resolved(args.root),
            "llama_server": cfg.llama_server.resolved(args.root),
            "setup": cfg.setup.resolved(args.root),
        }
        cfg = cfg.model_copy(update=resolved)
        persona = load_persona(args.root / cfg.persona.file)
        with ExitStack() as files:
            log_file = files.enter_context(_open(args.root / cfg.logging.file))
            files.enter_context(logging_to(cfg.logging, log_file))
            _warn_ignored(ignored_user_keys(edition_files(args.root / "config", edition)))
            traces = files.enter_context(_open(args.root / cfg.telemetry.traces_file))
            return asyncio.run(_run(args.mode, cfg, persona, console, traces))
    except ConfigError as exc:  # в т.ч. неизвестный `[llm].backend` — выясняется при сборке
        print(f"Ошибка конфигурации: {exc}", file=console.out)
        return EXIT_CONFIG


async def _run(
    mode: str, cfg: AppConfig, persona: Persona, console: Console, traces: TextIO
) -> int:
    bus = EventBus()
    core = Core(bus, Telemetry(bus))
    bus.subscribe(MetricRecorded, TraceWriter(traces))
    # Здесь, а не в TaskGroup: ошибка бюджета в конфиге должна дойти до main как ConfigError.
    resources = _resources(cfg, bus)
    # Голос — только у шлюза: терминальный чат звук не воспроизводит (S-7.5).
    voice = build_voice(cfg) if mode == SERVE_MODE else None
    async with (
        LlamaServerProcess(cfg.llama_server, cfg.llm.base_url) as server,
        llm_backends().create(cfg.llm.backend, cfg.llm) as llm,
        asyncio.TaskGroup() as tg,
    ):
        metrics = tg.create_task(core.telemetry.run())
        trimming = tg.create_task(resources.run(NvidiaSmiProbe(cfg.gpu_probe)))
        conversation = build_conversation(cfg, persona, with_voice(llm, voice), core)
        warmup = _Warmup(_Llm(llm, server), conversation.prompts, bus, voice)
        # Память (Этап 10): факты и резюме — в простое, LLM фонового слота; поиск — в ходе (T-12).
        async with (
            background_memory(cfg, conversation, core) as controls,
            running_plugins(cfg.plugins, bus, models=ResourceModels(resources)) as plugins,
        ):
            _connect_tools(cfg, conversation.service, plugins)
            if mode == SERVE_MODE:
                code = await _serve(
                    AppParts(
                        cfg, core, plugins, resources, controls, conversation.history, persona
                    ),
                    conversation.service,
                    warmup,
                    console,
                )
            else:
                code = await _chat(conversation.service, warmup, console, bus)
        metrics.cancel()
        trimming.cancel()
    return code


def _resources(cfg: AppConfig, bus: EventBus) -> ResourceManager:
    manager = ResourceManager(cfg.resources)
    manager.follow(bus)
    return manager


def _connect_tools(cfg: AppConfig, service: ConversationService, plugins: PluginServices) -> None:
    """Без инструментов сервис хода не тратит на них ни одного вызова."""
    if plugins.contexts:
        tools = ToolContext(plugins.contexts, cfg.plugins.context_timeout_s)
        service.use_tools(tools.hints)


async def _chat(
    service: ConversationService, warmup: "_Warmup", console: Console, bus: EventBus
) -> int:
    if (problem := await warmup.run()) is not None:
        print(f"LLM недоступна: {problem}", file=console.out)
        return EXIT_UNAVAILABLE
    await TerminalChat(service, bus, console.read_line, console.out).run()
    return 0


async def _serve(
    app: AppParts,
    service: ConversationService,
    warmup: "_Warmup",
    console: Console,
) -> int:
    """Шлюз живёт, пока открыт stdin: Tauri-родитель умер — pipe закрыт — ядро выходит."""
    cfg, core, plugins = app.cfg, app.core, app.plugins
    async with GatewayServer(service, warmup.bus, cfg.gateway) as server:
        connect_panels(app, server, service)
        print(f"Шлюз для UI: ws://{cfg.gateway.host}:{server.port}", file=console.out)
        if (problem := await warmup.run()) is not None:
            _log.warning("llm.unavailable_at_start", problem=problem)
        # Модель голоса грузится уже при открытом шлюзе: UI видит «TTS загружается».
        async with (
            warmup.voice(),
            voice_input(cfg, server, service, core) as hearing,
            asyncio.TaskGroup() as tg,
        ):
            supervising = tg.create_task(_supervisor(cfg, warmup, hearing).run())
            serving = tg.create_task(server.serve_forever())
            external = ExternalTurns(
                service, server.send, server.send_bytes, lambda: server.has_client
            )
            readers = [tg.create_task(external.run(stream)) for stream in plugins.sources]
            initiative = connect_initiative(app, server, service, external)
            if initiative is not None:
                readers.append(tg.create_task(_forever(initiative)))
            while await console.read_line() is not None:
                pass
            serving.cancel()
            supervising.cancel()
            for reader in readers:
                reader.cancel()
    return 0


async def _forever(initiative: Initiative) -> None:
    await initiative.run()


def _supervisor(cfg: AppConfig, warmup: "_Warmup", hearing: Supervised | None) -> Supervisor:
    """Наблюдаем за тем, что можем поднять: внешний llama-server ядру не подчиняется."""
    items = [*warmup.supervised(), *([hearing] if hearing is not None else [])]
    return Supervisor(items if cfg.supervisor.enabled else (), cfg.supervisor, warmup.bus)


@dataclass(frozen=True, slots=True)
class _Llm:
    """Модель и её сервер: прогрев сначала ждёт, пока сервер, запущенный ядром, поднимется."""

    port: LLMPort
    server: LlamaServerProcess


class _Warmup:
    """Прогрев бэкендов (T-06) со статусами для UI: загружается → готов / сбой.

    LLM — прогрев префикса промпта; голос — загрузка модели на время работы шлюза и синтез
    междометий (T-17).
    """

    def __init__(
        self, llm: _Llm, prompts: PromptBuilder, bus: EventBus, voice: VoiceParts | None
    ) -> None:
        self._llm = llm
        self._prefix = prompts.prefix
        self._texts = prompts.texts
        self.bus = bus
        self._voice = voice

    def supervised(self) -> list[Supervised]:
        """Что из прогретого подчиняется ядру и может быть поднято заново (S-17.1)."""
        items: list[Supervised] = []
        if self._llm.server.started:
            items.append(LlmSupervised(self._llm.server, self.run))
        if self._voice is not None:
            items.append(TtsSupervised(self._voice.tts, self._voice.flag))
        return items

    async def run(self) -> str | None:
        """None — LLM готова; иначе — текст проблемы."""
        await self.bus.publish(BackendStatusChanged(Component.LLM, BackendState.LOADING))
        try:
            await self._llm.server.wait_ready()
            warmup = Message(Role.USER, self._texts.warmup_user)
            await self._llm.port.prefill((*self._prefix, warmup))
        except LLMUnavailable as exc:
            await self.bus.publish(BackendStatusChanged(Component.LLM, BackendState.FAILED))
            return str(exc)
        await self.bus.publish(BackendStatusChanged(Component.LLM, BackendState.READY))
        _log.info("llm.ready")
        return None

    @asynccontextmanager
    async def voice(self) -> AsyncIterator[None]:
        """Модель голоса загружена, пока открыт контекст; без голоса — пустой контекст."""
        if self._voice is None:
            yield
            return
        await self._tts_status(BackendState.LOADING)
        async with self._voice.tts as tts:
            try:
                async with aclosing(tts.synthesize(self._texts.tts_probe)) as audio:
                    async for _ in audio:
                        pass
                await self._voice.fillers.prepare(tts)
            except (TTSUnavailable, GenerationFailed) as exc:
                _log.warning("tts.unavailable_at_start", problem=str(exc))
                await self._tts_status(BackendState.FAILED)
            else:
                _log.info("tts.ready")
                await self._tts_status(BackendState.READY)
            yield

    async def _tts_status(self, state: BackendState) -> None:
        await self.bus.publish(BackendStatusChanged(Component.TTS, state))


def _open(path: Path) -> TextIO:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.open("a", encoding="utf-8")


def _parse(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="vtuber", description=__doc__)
    parser.add_argument("mode", nargs="?", choices=(CHAT_MODE, SERVE_MODE), default=CHAT_MODE)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="корень проекта (config/)")
    parser.add_argument("--edition", help="издание: ru | en (иначе VTUBER_EDITION__ID, иначе ru)")
    return parser.parse_args(argv)


def _warn_ignored(keys: list[str]) -> None:
    if keys:  # общий user.toml писался для русского издания: эти ключи — в user.<издание>.toml
        _log.warning("config.user_keys_ignored", keys=keys)


def run() -> int:
    """Запуск из консоли: `python -m vtuber [chat|serve] [--root путь]`."""
    return main(sys.argv[1:], os.environ, Console(sys.stdin, sys.stdout))
