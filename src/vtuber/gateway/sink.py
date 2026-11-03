"""WsReplySink: ответ хода → сообщения протокола и бинарные аудиокадры для UI."""

from collections.abc import Awaitable, Callable

from vtuber.domain import AudioChunk, Emotion, Gesture, TurnId, TurnStateError
from vtuber.gateway.codec import encode_audio_frame
from vtuber.gateway.protocol import AvatarEmotion, ChatDelta, OutboundMessage, turn_ref
from vtuber.gateway.protocol_avatar import AvatarGesture
from vtuber.kernel import current_turn

type Send = Callable[[OutboundMessage], Awaitable[None]]
type SendBytes = Callable[[bytes], Awaitable[None]]


class WsReplySink:
    """ReplySink для WebSocket: текст → `chat.delta`, эмоция → `avatar.emotion`, звук → кадр.

    Один экземпляр на ход: `seq` аудиокадров считается с нуля в каждом ходе (ADR-0003, без base64).
    Номер хода берётся из `kernel.current_turn()` — сервис хода выставляет его на время задачи
    хода. `done` ничего не шлёт: конец хода UI узнаёт из `turn.finished` (событие шины).
    """

    def __init__(self, send: Send, send_bytes: SendBytes) -> None:
        self._send = send
        self._send_bytes = send_bytes
        self._seq = 0

    async def text(self, delta: str) -> None:
        """Порция текста → `chat.delta`."""
        await self._send(ChatDelta.of(turn_ref(_turn()), delta))

    async def emotion(self, emotion: Emotion) -> None:
        """Смена эмоции → `avatar.emotion`."""
        await self._send(AvatarEmotion.of(turn_ref(_turn()), emotion))

    async def gesture(self, gesture: Gesture) -> None:
        """Жест → `avatar.gesture`."""
        await self._send(AvatarGesture.of(turn_ref(_turn()), gesture))

    async def audio(self, chunk: AudioChunk) -> None:
        """Фрагмент речи → бинарный кадр `<BBHIQ` + PCM (docs/protocol.md)."""
        frame = encode_audio_frame(_turn(), self._seq, chunk)
        self._seq += 1
        await self._send_bytes(frame)

    async def done(self) -> None:
        """Конец ответа сообщает `turn.finished` из шины."""


def _turn() -> TurnId:
    turn_id = current_turn()
    if turn_id is None:
        msg = "WsReplySink вызван вне хода — его зовёт только конвейер внутри задачи хода"
        raise TurnStateError(msg)
    return turn_id
