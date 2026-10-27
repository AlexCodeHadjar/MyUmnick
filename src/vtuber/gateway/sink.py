"""WsReplySink: ответ хода → сообщения протокола для UI."""

from collections.abc import Awaitable, Callable

from vtuber.domain import Emotion, TurnStateError
from vtuber.gateway.protocol import AvatarEmotion, ChatDelta, OutboundMessage, turn_ref
from vtuber.kernel import current_turn

type Send = Callable[[OutboundMessage], Awaitable[None]]


class WsReplySink:
    """ReplySink для WebSocket: текст → `chat.delta`, эмоция → `avatar.emotion`.

    Номер хода берётся из `kernel.current_turn()` — сервис хода выставляет его на время задачи
    хода. `done` ничего не шлёт: конец хода UI узнаёт из `turn.finished` (событие шины).
    """

    def __init__(self, send: Send) -> None:
        self._send = send

    async def text(self, delta: str) -> None:
        """Порция текста → `chat.delta`."""
        await self._send(ChatDelta.of(_turn(), delta))

    async def emotion(self, emotion: Emotion) -> None:
        """Смена эмоции → `avatar.emotion`."""
        await self._send(AvatarEmotion.of(_turn(), emotion))

    async def done(self) -> None:
        """Конец ответа сообщает `turn.finished` из шины."""


def _turn() -> str:
    turn_id = current_turn()
    if turn_id is None:
        msg = "WsReplySink вызван вне хода — его зовёт только конвейер внутри задачи хода"
        raise TurnStateError(msg)
    return turn_ref(turn_id)
