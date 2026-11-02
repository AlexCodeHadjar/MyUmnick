"""Голосовой ввод в `serve` (Этап 11): модели грузятся при первом кадре микрофона.

Whisper turbo занимает VRAM и секунды старта: пока пользователь не включил микрофон, платить за неё
незачем. Статус `stt` показывает загрузку в UI; кадры, пришедшие за это время, ждут в очереди.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from vtuber.adapters.stt import SileroVad, WhisperSTT
from vtuber.application.conversation import ConversationService
from vtuber.application.voice import VoiceEvents, VoiceListener
from vtuber.bootstrap.config import SttConfig
from vtuber.bootstrap.container import Core
from vtuber.domain import AudioChunk, BackendState, BackendStatusChanged, Component
from vtuber.gateway import GatewayServer, VoiceBridge
from vtuber.kernel import get_logger

_log = get_logger(__name__)


class _LazyVoice:
    """Первый кадр запускает загрузку; дальше кадры уходят слушателю (до него — в очередь)."""

    def __init__(self, cfg: SttConfig, events: VoiceEvents, core: Core) -> None:
        self._cfg = cfg
        self._events = events
        self._core = core
        self._task: asyncio.Task[None] | None = None
        self._early: list[AudioChunk] = []
        self._listener: VoiceListener | None = None

    async def on_frame(self, chunk: AudioChunk) -> None:
        if self._listener is not None:
            self._listener.feed(chunk)
            return
        self._early.append(chunk)
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.wait([self._task])

    async def _status(self, state: BackendState) -> None:
        await self._core.bus.publish(BackendStatusChanged(Component.STT, state))

    async def _run(self) -> None:
        await self._status(BackendState.LOADING)
        async with SileroVad(self._cfg.vad) as vad, WhisperSTT(self._cfg.whisper) as stt:
            listener = VoiceListener(vad, stt, self._events, self._cfg.voice)
            for chunk in self._early:
                listener.feed(chunk)
            self._early.clear()
            self._listener = listener
            await self._status(BackendState.READY)
            _log.info("voice.ready")
            await listener.run()


@asynccontextmanager
async def voice_input(
    cfg: SttConfig, server: GatewayServer, service: ConversationService, core: Core
) -> AsyncIterator[None]:
    """Подключает микрофон к шлюзу на время контекста; выключено в конфиге — кадры не нужны."""
    if not cfg.enabled:
        yield
        return
    bridge = VoiceBridge(service, server.send, server.send_bytes, core.telemetry)
    voice = _LazyVoice(cfg, bridge, core)
    server.on_mic(voice.on_frame)
    try:
        yield
    finally:
        await voice.stop()
