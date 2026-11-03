"""Помощник-программист (S-12.6): просьба — отдельной модели, код — в чат, голосом — только фраза.

Работает вне горячего пути: справка хода отвечает сразу, а задача идёт своей задачей. Модель
выбирается в S-12.5; плагин знает о ней только адрес и объём из настроек.
"""

import asyncio
import re
from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, aclosing
from pathlib import Path
from types import TracebackType
from typing import Final, Self

from pydantic import Field

from vtuber.adapters.llm import LlamaCppLLM, LlamaServerConfig, LlamaServerProcess, LLMConfig
from vtuber.adapters.llm import OpenAICompatLLM as _OpenAI
from vtuber.domain import IncomingMessage, Message, Role, VtuberError
from vtuber.kernel import ConfigSection, PluginContext
from vtuber.ports import GenerationParams, LLMPort

_REQUEST: Final = re.compile(
    r"\b(?:напиши|набросай|сделай)\s+(?:мне\s+)?(?:код|функцию|скрипт|программу|класс)\b"
    r"|\bпомоги\s+с\s+кодом\b"
    r"|\b(?:исправь|почини)\s+(?:этот\s+|мой\s+)?код\b",
    re.IGNORECASE,
)
_CANCEL: Final = ("отмени код", "Отмени код")
_STARTED: Final = (
    "Ты передала эту просьбу помощнику-программисту, ответ появится в чате позже. "
    "Скажи об этом одной фразой и сама код не пиши."
)
_BUSY: Final = "Помощник-программист ещё занят прошлой задачей. Скажи об этом одной фразой."
_TRANSLATE: Final = (
    "Translate the programming request to English. Keep names and code as they are. "
    "Reply with the translation only."
)
_CODE_SYSTEM: Final = "You are a senior programmer. Reply in English with working code."
_AUTHOR: Final = "помощник"


class CodeAssistantConfig(ConfigSection):
    """Секция `[plugins.settings.code_assistant]`.

    `server` — поднимать llama-server на время задачи; нет — он уже запущен на `code_url`.
    `vram_mb` — объём модели из замера S-12.5 для менеджера ресурсов.
    """

    main_url: str = "http://127.0.0.1:8080"
    translate_slot: int = Field(default=1, ge=0)
    code_url: str = "http://127.0.0.1:8081"
    code_model: str = "code"
    max_tokens: int = Field(default=1024, gt=0)
    timeout_s: float = Field(default=300.0, gt=0)
    vram_mb: int = Field(default=6000, gt=0)
    server: LlamaServerConfig | None = None


def asks_for_code(text: str) -> bool:
    """Только явная просьба: обычное упоминание кода задачу не запускает."""
    return _REQUEST.search(text) is not None


def _llm_config(url: str, model: str, slot: int, timeout_s: float) -> LLMConfig:
    return LLMConfig.model_validate(
        {
            "backend": "llamacpp",
            "base_url": url,
            "model": model,
            "connect_timeout_s": 5.0,
            "read_timeout_s": timeout_s,
            "generation": {"max_tokens": 128, "temperature": 0.2},
            "llamacpp": {
                "slot_id": slot,
                "enable_thinking": False,
                "forbid_foreign_scripts": False,
            },
        }
    )


async def _complete(llm: LLMPort, messages: list[Message], max_tokens: int) -> str:
    params = GenerationParams(max_tokens=max_tokens, temperature=0.2)
    async with aclosing(llm.stream(messages, params)) as deltas:
        return "".join([delta async for delta in deltas])


class _CodeServer:
    """Процесс модели для менеджера ресурсов: новый на каждую загрузку, у него свой HTTP-клиент."""

    def __init__(self, cfg: LlamaServerConfig, url: str) -> None:
        self._cfg = cfg.resolved(Path.cwd())
        self._url = url
        self._process: LlamaServerProcess | None = None

    async def load(self) -> None:
        """Запустить и дождаться готовности."""
        process = LlamaServerProcess(self._cfg, self._url)
        await process.__aenter__()
        self._process = process
        await process.wait_ready()

    async def unload(self) -> None:
        """Остановить: видеопамять свободна."""
        process, self._process = self._process, None
        if process is not None:
            await process.__aexit__(None, None, None)


class _Worker:
    """Одна задача за раз; отмена закрывает поток, и сервер прекращает генерацию (T-14)."""

    def __init__(self, ctx: PluginContext, cfg: CodeAssistantConfig) -> None:
        self._ctx = ctx
        self._cfg = cfg
        self._translator = LlamaCppLLM(
            _llm_config(cfg.main_url, "main", cfg.translate_slot, cfg.timeout_s)
        )
        self._coder = _OpenAI(_llm_config(cfg.code_url, cfg.code_model, 0, cfg.timeout_s))
        self._job: asyncio.Task[None] | None = None
        self.finished: asyncio.Queue[IncomingMessage] = asyncio.Queue()
        self._hold: Callable[[], AbstractAsyncContextManager[None]] | None = None
        if cfg.server is not None and ctx.models is not None:
            self._hold = ctx.models.hold(
                "code_assistant", cfg.vram_mb, _CodeServer(cfg.server, cfg.code_url)
            )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.cancel()
        await self._translator.__aexit__(None, None, None)
        await self._coder.__aexit__(None, None, None)

    @property
    def busy(self) -> bool:
        """Идёт ли задача."""
        return self._job is not None and not self._job.done()

    def start(self, task: str) -> None:
        """Запустить, не дожидаясь: ход не ждёт помощника."""
        self._job = asyncio.create_task(self._work(task))

    async def cancel(self) -> None:
        """Остановить задачу; не идёт — ничего не делает."""
        if self.busy and self._job is not None:
            self._job.cancel()
            await asyncio.wait({self._job})

    async def _work(self, task: str) -> None:
        try:
            async with asyncio.timeout(self._cfg.timeout_s):
                code = await self._write(task)
        except TimeoutError:
            await self._say("Помощник-программист не уложился в срок. Скажи об этом одной фразой.")
        except (VtuberError, OSError) as exc:
            self._ctx.log.warning("code_assistant.failed", problem=repr(exc))
            await self._say(
                "Помощник-программист сейчас недоступен. Честно скажи об этом одной фразой."
            )
        else:
            await self._ctx.show_text("Помощник-программист", code)
            await self._say(
                "Код от помощника уже в чате. Скажи об этом одной фразой, код не читай."
            )

    async def _write(self, task: str) -> str:
        ask = [Message(Role.SYSTEM, _TRANSLATE), Message(Role.USER, task)]
        english = await _complete(self._translator, ask, 256)
        prompt = [Message(Role.SYSTEM, _CODE_SYSTEM), Message(Role.USER, english.strip())]
        if self._hold is None:
            return await _complete(self._coder, prompt, self._cfg.max_tokens)
        async with self._hold():
            return await _complete(self._coder, prompt, self._cfg.max_tokens)

    async def _say(self, text: str) -> None:
        await self.finished.put(IncomingMessage(self._ctx.name, _AUTHOR, text, is_viewer=False))


class CodeAssistantPlugin:
    """Инструмент помощника; выключен, пока его не включат, и в диалог ничего не добавляет."""

    name = "code_assistant"

    def __init__(self) -> None:
        self._worker: _Worker | None = None

    async def setup(self, ctx: PluginContext) -> None:
        """HTTP-клиенты создаются здесь: на Windows это почти секунда и не должно попасть в ход."""
        self._worker = _Worker(ctx, ctx.settings(CodeAssistantConfig))
        ctx.add_context(self.context)
        ctx.add_source(self.results)
        for text in _CANCEL:
            ctx.add_command(text, self._worker.cancel)

    async def shutdown(self) -> None:
        """Остановить задачу и закрыть соединения."""
        if self._worker is not None:
            await self._worker.__aexit__(None, None, None)

    async def context(self, text: str) -> str | None:
        """Обычная реплика ничего не стоит: одна проверка по шаблону."""
        worker = self._worker
        if worker is None or not asks_for_code(text):
            return None
        if worker.busy:
            return _BUSY
        worker.start(text)
        return _STARTED

    async def results(self) -> AsyncGenerator[IncomingMessage]:
        """Что сказать вслух, когда задача закончилась; сам код сюда не попадает."""
        worker = self._worker
        while worker is not None:
            yield await worker.finished.get()
