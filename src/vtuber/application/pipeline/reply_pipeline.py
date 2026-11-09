"""Конвейер хода: поток LLM → разбор тегов → получатель; с голосом — ещё нарезка и TTS (T-02)."""

import asyncio
from collections.abc import Sequence
from contextlib import aclosing
from dataclasses import dataclass, replace

from vtuber.application.pipeline.chunker import ChunkerConfig, SentenceChunker
from vtuber.application.pipeline.filler import FillerBank
from vtuber.application.pipeline.speaker import Delivery, PhraseListener, PhraseQueue, Speaker
from vtuber.application.pipeline.stream_parser import ParseEvent, StreamParser
from vtuber.application.speech import RU_DICTION, Diction
from vtuber.domain import Message
from vtuber.kernel import Telemetry, get_logger
from vtuber.ports import GenerationParams, LLMPort, ReplySink, TTSPort

_log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Voice:
    """Голос хода: движок TTS, нарезка на фразы, междометия (T-17); без голоса — только текст."""

    tts: TTSPort
    chunker: ChunkerConfig
    fillers: FillerBank | None = None
    on_phrase: PhraseListener | None = None
    diction: Diction = RU_DICTION


@dataclass(frozen=True, slots=True)
class _Request:
    """Запрос к LLM на один ход."""

    messages: Sequence[Message]
    params: GenerationParams


class _PhraseFeed:
    """Текст для озвучки → готовые фразы в очередь TTS-ветки; без голоса — ничего не делает."""

    def __init__(self, chunker: SentenceChunker | None, queue: PhraseQueue | None) -> None:
        self._chunker = chunker
        self._queue = queue

    def add(self, spoken_text: str) -> None:
        if self._chunker is None or self._queue is None:
            return
        for phrase in self._chunker.feed(spoken_text):
            self._queue.put_nowait(phrase)

    def close(self) -> None:
        """Конец ответа: хвост — последней фразой, затем маркер конца."""
        if self._chunker is None or self._queue is None:
            return
        if tail := self._chunker.flush():
            self._queue.put_nowait(tail)
        self._queue.put_nowait(None)


_NO_VOICE = _PhraseFeed(None, None)


class ReplyPipeline:
    """Стримит ответ LLM получателю по мере генерации (T-01): ни одна стадия не ждёт конца.

    С голосом фразы уходят в TTS-задачу сразу по готовности: синтез фразы N идёт параллельно с
    генерацией N+1 (T-02). Отмена задачи хода закрывает поток LLM — сервер прекращает генерацию
    (T-14) — и отменяет синтез; `done` при отмене и ошибке не отправляется. Ход кончается, когда
    отдан последний звук. Замеры: `llm.first_token` (TTFT), `llm.stream`, `tts.*` (Speaker).
    """

    def __init__(
        self,
        llm: LLMPort,
        params: GenerationParams,
        telemetry: Telemetry,
        voice: Voice | None = None,
    ) -> None:
        self._llm = llm
        self._params = params
        self._telemetry = telemetry
        self._voice = voice

    async def run(
        self,
        messages: Sequence[Message],
        sink: ReplySink,
        parser: StreamParser,
        temperature: float | None = None,
    ) -> None:
        """Отдаёт ответ в `sink`; `parser` — состояние хода у вызывающего.

        `temperature` — на этот ход вместо обычной (вопрос о фактах, S-10.5).

        После завершения, ошибки или отмены `parser.full_text` — показанная часть ответа для
        истории. Ошибки TTS ход не обрывают (Speaker).

        Raises:
            LLMUnavailable: LLM-сервер недоступен.
            GenerationFailed: генерация сорвалась посреди ответа.

        """
        params = (
            self._params if temperature is None else replace(self._params, temperature=temperature)
        )
        request = _Request(messages, params)
        voice = self._voice
        if voice is None:
            await self._write(request, sink, parser, _NO_VOICE)
            await sink.done()
            return
        phrases: PhraseQueue = asyncio.Queue()
        delivery = Delivery(voice.fillers, voice.on_phrase, voice.diction.normalize)
        speaker = Speaker(voice.tts, self._telemetry, delivery)
        speaking = asyncio.create_task(speaker.run(phrases, sink))
        try:
            chunker = SentenceChunker(voice.chunker, voice.diction.abbreviations)
            feed = _PhraseFeed(chunker, phrases)
            await self._write(request, sink, parser, feed)
            await speaking
        finally:
            await _stop(speaking)
        await sink.done()

    async def prefill(self, messages: Sequence[Message]) -> None:
        """Прогрев кэша LLM промптом без генерации (T-05): ход по такому промпту начнётся быстрее.

        Raises:
            LLMUnavailable: LLM-сервер недоступен.
            GenerationFailed: сервер ответил ошибкой.

        """
        with self._telemetry.span("llm.prefill"):
            await self._llm.prefill(messages)

    async def _write(
        self, request: _Request, sink: ReplySink, parser: StreamParser, feed: _PhraseFeed
    ) -> None:
        async with aclosing(self._llm.stream(request.messages, request.params)) as stream:
            with self._telemetry.span("llm.stream"):
                with self._telemetry.span("llm.first_token"):
                    first = await anext(stream, None)
                if first is not None:
                    await _deliver(parser.feed(first), sink, feed)
                async for delta in stream:
                    await _deliver(parser.feed(delta), sink, feed)
        await _deliver(parser.flush(), sink, feed)
        feed.close()


async def _deliver(events: Sequence[ParseEvent], sink: ReplySink, feed: _PhraseFeed) -> None:
    for event in events:
        await event.deliver(sink)
        feed.add(event.spoken_text)


async def _stop(task: asyncio.Task[None]) -> None:
    """Отменить TTS-задачу, если она ещё идёт, и дождаться: синтез закрыт до конца хода (T-14)."""
    if not task.done():
        task.cancel()
    await asyncio.wait([task])
    if not task.cancelled() and (error := task.exception()) is not None:
        _log.error("tts.branch_failed", error=repr(error))
