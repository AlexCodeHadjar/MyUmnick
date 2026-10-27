"""Конвейер хода: поток LLM → разбор тегов → получатель (текстовая ветка; TTS — S-7.5)."""

from collections.abc import Sequence
from contextlib import aclosing

from vtuber.application.pipeline.stream_parser import ParseEvent, StreamParser
from vtuber.domain import Message
from vtuber.kernel import Telemetry
from vtuber.ports import GenerationParams, LLMPort, ReplySink


class ReplyPipeline:
    """Стримит ответ LLM получателю по мере генерации (T-01): ни одна стадия не ждёт конца.

    Отмена задачи хода закрывает поток LLM — сервер прекращает генерацию (T-14); `done` при
    отмене и ошибке не отправляется. Замеры: `llm.first_token` (TTFT) и `llm.stream`.
    """

    def __init__(self, llm: LLMPort, params: GenerationParams, telemetry: Telemetry) -> None:
        self._llm = llm
        self._params = params
        self._telemetry = telemetry

    async def run(self, messages: Sequence[Message], sink: ReplySink, parser: StreamParser) -> None:
        """Отдаёт ответ в `sink`; `parser` — состояние хода у вызывающего.

        После завершения, ошибки или отмены `parser.full_text` — показанная часть ответа для
        истории.

        Raises:
            LLMUnavailable: LLM-сервер недоступен.
            GenerationFailed: генерация сорвалась посреди ответа.

        """
        async with aclosing(self._llm.stream(messages, self._params)) as stream:
            with self._telemetry.span("llm.stream"):
                with self._telemetry.span("llm.first_token"):
                    first = await anext(stream, None)
                if first is not None:
                    await _deliver(parser.feed(first), sink)
                async for delta in stream:
                    await _deliver(parser.feed(delta), sink)
        await _deliver(parser.flush(), sink)
        await sink.done()


async def _deliver(events: Sequence[ParseEvent], sink: ReplySink) -> None:
    for event in events:
        await event.deliver(sink)
