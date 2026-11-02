"""Голосовой ввод ↔ шлюз (Этап 11): события слушателя → сообщения UI и ход диалога."""

import time
from collections.abc import Awaitable, Callable

from vtuber.application.conversation import ConversationService
from vtuber.domain import AudioChunk, CancelReason, Emotion
from vtuber.gateway.protocol import InputBargeIn, InputFinal, InputHypothesis, OutboundMessage
from vtuber.gateway.sink import WsReplySink
from vtuber.kernel import Telemetry
from vtuber.ports import ReplySink

END_TO_AUDIO_SPAN = "voice.end_to_audio"
"""От конца речи пользователя до первого звука ответа в ядре (Этап 11: p50 ≤ 1.5 с)."""


class VoiceBridge:
    """Реализует `VoiceEvents`: перебивание, гипотезы в UI, финальная фраза — новый ход."""

    def __init__(
        self,
        service: ConversationService,
        send: Callable[[OutboundMessage], Awaitable[None]],
        send_bytes: Callable[[bytes], Awaitable[None]],
        telemetry: Telemetry,
    ) -> None:
        self._service = service
        self._send = send
        self._send_bytes = send_bytes
        self._telemetry = telemetry

    async def barge_in(self) -> None:
        """Сначала сообщить UI — он глушит голос сразу; затем отменить ход, если он идёт."""
        await self._send(InputBargeIn.of())
        await self._service.cancel(CancelReason.BARGE_IN)

    async def hypothesis(self, text: str) -> None:
        """Показать, что слышно, и прогреть кэш LLM тем же текстом (T-05)."""
        await self._send(InputHypothesis.of(text))
        self._service.typing(text)

    async def final(self, text: str, ended_ns: int) -> None:
        """Фраза становится репликой: в чат UI и в ход, с замером до первого звука."""
        await self._send(InputFinal.of(text))
        inner = WsReplySink(self._send, self._send_bytes)
        sink = _FirstAudioSink(inner, self._telemetry, ended_ns)
        await self._service.handle(text, sink)


class _FirstAudioSink:
    """Пропускает всё в `inner`; на первом звуке пишет `voice.end_to_audio`."""

    def __init__(self, inner: ReplySink, telemetry: Telemetry, ended_ns: int) -> None:
        self._inner = inner
        self._telemetry = telemetry
        self._ended_ns = ended_ns
        self._measured = False

    async def text(self, delta: str) -> None:
        await self._inner.text(delta)

    async def emotion(self, emotion: Emotion) -> None:
        await self._inner.emotion(emotion)

    async def audio(self, chunk: AudioChunk) -> None:
        if not self._measured:
            self._measured = True
            self._telemetry.record(END_TO_AUDIO_SPAN, time.perf_counter_ns() - self._ended_ns)
        await self._inner.audio(chunk)

    async def done(self) -> None:
        await self._inner.done()
