"""Сервис хода диалога: жизненный цикл, отмена предыдущего хода, история и события."""

import asyncio
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from itertools import count
from typing import Final

from vtuber.application.memory import ShortTermMemory, TurnHints
from vtuber.application.pipeline import ReplyPipeline, StreamParser
from vtuber.application.prompting import PromptBuilder
from vtuber.domain import (
    AudioChunk,
    CancelReason,
    Emotion,
    Message,
    Turn,
    TurnCancelled,
    TurnFinished,
    TurnId,
    TurnRemembered,
    TurnStarted,
    TurnState,
    VtuberError,
    next_state,
)
from vtuber.kernel import EventBus, get_logger, turn_context
from vtuber.ports import ReplySink

type HintSource = Callable[[str], Awaitable[TurnHints]]
"""Что долговременная память добавляет ходу по реплике (`MemoryRecall.hints`)."""

INTERNAL_ERROR_MESSAGE: Final = "Внутренняя ошибка при ответе — подробности в logs/app.jsonl"

_log = get_logger(__name__)


@dataclass(slots=True)
class _ActiveTurn:
    id: TurnId
    user_text: str
    sink: ReplySink
    parser: StreamParser = field(default_factory=StreamParser)
    reason: CancelReason = CancelReason.USER_STOP
    task: asyncio.Task[None] | None = None


class ConversationService:
    """Точка входа сценария «ход диалога» (docs/architecture.md, жизненный цикл хода).

    Сервис сам владеет задачей текущего хода (R-35): новая реплика отменяет предыдущий ход и
    дожидается его завершения (T-14). В историю идёт показанная часть ответа (`full_text`
    с тегами), прерванный ответ — с пометкой. Ошибка хода не роняет приложение: она становится
    `TurnCancelled(ERROR, message)`. Между ходами черновик реплики прогревает кэш LLM (T-05).
    """

    def __init__(
        self,
        pipeline: ReplyPipeline,
        prompts: PromptBuilder,
        memory: ShortTermMemory,
        bus: EventBus,
    ) -> None:
        self._pipeline = pipeline
        self._prompts = prompts
        self._memory = memory
        self._bus = bus
        self._ids = count(1)
        self._current: _ActiveTurn | None = None
        self._state = TurnState.IDLE
        self._prefill: asyncio.Task[None] | None = None
        self._prefilled: str | None = None
        self._hints: HintSource | None = None
        self._silent_at = 0.0

    @property
    def state(self) -> TurnState:
        """Состояние текущего хода."""
        return self._state

    def use_memory(self, hints: HintSource) -> None:
        """Подключить долговременную память (её собирает bootstrap, когда загружены модели)."""
        self._hints = hints

    async def handle(self, user_text: str, sink: ReplySink) -> TurnId:
        """Начинает ход по реплике; текущий ход (если идёт) прерывается. Не ждёт ответа."""
        await self.cancel(CancelReason.NEW_MESSAGE)
        self._stop_prefill()
        turn = _ActiveTurn(TurnId(next(self._ids)), user_text, sink)
        self._move(TurnState.THINKING)
        turn.task = asyncio.create_task(self._run(turn))
        self._current = turn
        return turn.id

    def typing(self, draft: str) -> None:
        """Черновик реплики: прогреть кэш LLM промптом с ним (T-05), не дожидаясь результата.

        Только между ходами: слот LLM занят генерацией, а история ещё не дополнена ответом.
        Новый черновик отменяет устаревший прогрев; тот же черновик повторно не греется.
        """
        text = draft.strip()
        if self._state is not TurnState.IDLE or not text or text == self._prefilled:
            return
        self._stop_prefill()
        self._prefilled = text
        messages = self._prompts.build(self._memory.messages, text).messages
        self._prefill = asyncio.create_task(self._warm(messages))

    async def cancel(self, reason: CancelReason) -> bool:
        """Прерывает текущий ход и ждёт его завершения; False — прерывать было нечего."""
        self._silent_at = 0.0  # UI глушит звук сразу при отмене и новом ходе
        turn = self._current
        if turn is None or turn.task is None or turn.task.done():
            return False
        turn.reason = reason
        turn.task.cancel()
        await asyncio.wait({turn.task})
        return True

    async def wait_idle(self) -> None:
        """Ждёт завершения текущего хода (тесты, завершение приложения)."""
        if self._current is not None and self._current.task is not None:
            await asyncio.wait({self._current.task})

    async def wait_silent(self) -> None:
        """Ждёт конца хода и конца его звука: синтез быстрее речи (RTF 0.02), ход кончается раньше.

        Новый ход вытесняет звук прошлого в UI, поэтому реплика не от ведущего ждёт этой тишины.
        """
        await self.wait_idle()
        while (left := self._silent_at - time.monotonic()) > 0:
            await asyncio.sleep(left)
            await self.wait_idle()

    async def _warm(self, messages: Sequence[Message]) -> None:
        try:
            await self._pipeline.prefill(messages)
        except VtuberError as exc:
            # Прогрев — догадка: не вышел — ход просто начнётся без него.
            _log.info("prefill.skipped", problem=str(exc))

    def _stop_prefill(self) -> None:
        """Устаревший прогрев больше не нужен; следующий черновик греется заново."""
        if self._prefill is not None and not self._prefill.done():
            self._prefill.cancel()
        self._prefill = None
        self._prefilled = None

    async def _run(self, turn: _ActiveTurn) -> None:
        with turn_context(turn.id):
            try:
                await self._bus.publish(TurnStarted(turn.id))
                hints = TurnHints() if self._hints is None else await self._hints(turn.user_text)
                prompt = self._prompts.build(self._memory.messages, turn.user_text, hints.context)
                sink = _FirstOutputSink(turn.sink, self._start_speaking, self._count_audio)
                await self._pipeline.run(prompt.messages, sink, turn.parser, hints.temperature)
            except asyncio.CancelledError:
                await self._stop(turn, TurnCancelled(turn.id, turn.reason), remember=True)
                raise
            except VtuberError as exc:
                await self._fail(turn, str(exc))
            except Exception:  # noqa: BLE001 — R-42: верхняя граница хода, с логом и turn_id
                _log.exception("turn.crashed")
                await self._fail(turn, INTERNAL_ERROR_MESSAGE)
            else:
                await self._remember(Turn(turn.id, turn.user_text, turn.parser.full_text))
                self._move(TurnState.IDLE)
                await self._bus.publish(TurnFinished(turn.id))

    async def _fail(self, turn: _ActiveTurn, message: str) -> None:
        _log.warning("turn.failed", message=message)
        event = TurnCancelled(turn.id, CancelReason.ERROR, message)
        await self._stop(turn, event, remember=bool(turn.parser.full_text))

    async def _stop(self, turn: _ActiveTurn, event: TurnCancelled, *, remember: bool) -> None:
        if remember:
            reply = turn.parser.full_text
            await self._remember(Turn(turn.id, turn.user_text, reply, is_interrupted=True))
        self._move(TurnState.CANCELLED)
        self._move(TurnState.IDLE)
        await self._bus.publish(event)

    async def _remember(self, turn: Turn) -> None:
        """В историю — и на шину: фоновая память извлечёт факты и сожмёт отрезанное (T-13)."""
        dropped = self._memory.append(turn)
        await self._bus.publish(TurnRemembered(turn, dropped))

    def _count_audio(self, chunk: AudioChunk) -> None:
        self._silent_at = max(self._silent_at, time.monotonic()) + chunk.duration_s

    def _start_speaking(self) -> None:
        self._move(TurnState.SPEAKING)

    def _move(self, target: TurnState) -> None:
        self._state = next_state(self._state, target)


@dataclass(slots=True)
class _FirstOutputSink:
    """Пропускает всё в `inner`; на первом выводе ответа зовёт `on_first` (THINKING → SPEAKING)."""

    inner: ReplySink
    on_first: Callable[[], None]
    on_audio: Callable[[AudioChunk], None]
    started: bool = False

    async def text(self, delta: str) -> None:
        self._mark()
        await self.inner.text(delta)

    async def emotion(self, emotion: Emotion) -> None:
        self._mark()
        await self.inner.emotion(emotion)

    async def audio(self, chunk: AudioChunk) -> None:
        self._mark()
        self.on_audio(chunk)
        await self.inner.audio(chunk)

    async def done(self) -> None:
        await self.inner.done()

    def _mark(self) -> None:
        if not self.started:
            self.started = True
            self.on_first()
