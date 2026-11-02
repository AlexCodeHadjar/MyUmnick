"""Протокол UI ↔ Ядро v1: модели сообщений — единственный источник схемы (TS-типы, docs)."""

from enum import StrEnum
from typing import Annotated, Final, Literal, Self

from pydantic import BaseModel, ConfigDict, Field

from vtuber.domain import BackendState, CancelReason, Component, Emotion, TurnId

PROTOCOL_VERSION: Final = 1
type Version = Literal[1]
"""Версия в каждом конверте; меняется вместе с `PROTOCOL_VERSION` при несовместимом изменении."""


def turn_ref(turn_id: TurnId) -> str:
    """Номер хода в JSON-сообщениях: `t-000042` (в аудиокадре — uint64)."""
    return f"t-{turn_id:06d}"


class ErrorCode(StrEnum):
    """Что пошло не так — UI выбирает реакцию по коду, текст показывает пользователю."""

    BAD_MESSAGE = "bad_message"
    LLM_UNAVAILABLE = "llm_unavailable"
    GENERATION_FAILED = "generation_failed"
    INTERNAL = "internal"


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EmptyData(_Model):
    """Сообщение без полезной нагрузки."""


class SendData(_Model):
    """Реплика пользователя."""

    text: str = Field(min_length=1)


class TypingData(_Model):
    """Черновик реплики, пока пользователь печатает; пустой — поле очищено."""

    text: str


class DeltaData(_Model):
    """Порция текста ответа."""

    text: str


class EmotionData(_Model):
    """Эмоция аватара; `intensity` 0…1 (затухание — Этап 8)."""

    emotion: Emotion
    intensity: float = Field(ge=0, le=1)


class CancelledData(_Model):
    """Почему ход прерван; `message` — текст ошибки при `reason == "error"`."""

    reason: CancelReason
    message: str


class SpanData(_Model):
    """Замер стадии хода для панели метрик (FR-15)."""

    name: str
    ms: float


class StatusData(_Model):
    """Состояние бэкенда для статус-бара."""

    component: Component
    state: BackendState


class ErrorData(_Model):
    """Ошибка для пользователя."""

    code: ErrorCode
    message: str


class ChatSend(_Model):
    """UI → Ядро: новая реплика; прерывает текущий ход."""

    v: Version
    type: Literal["chat.send"]
    data: SendData


class ChatCancel(_Model):
    """UI → Ядро: остановить ответ."""

    v: Version
    type: Literal["chat.cancel"]
    data: EmptyData


class InputTyping(_Model):
    """UI → Ядро: черновик реплики (с дебаунсом ~300 мс) — прогрев кэша LLM, T-05."""

    v: Version
    type: Literal["input.typing"]
    data: TypingData


type InboundMessage = Annotated[ChatSend | ChatCancel | InputTyping, Field(discriminator="type")]


class TurnStartedMessage(_Model):
    """Ядро → UI: ход начат — аватар «думает» (T-17)."""

    v: Version = PROTOCOL_VERSION
    type: Literal["turn.started"] = "turn.started"
    turn: str
    data: EmptyData

    @classmethod
    def of(cls, turn: str) -> Self:
        """Сообщение о начале хода `turn`."""
        return cls(turn=turn, data=EmptyData())


class ChatDelta(_Model):
    """Ядро → UI: порция текста ответа."""

    v: Version = PROTOCOL_VERSION
    type: Literal["chat.delta"] = "chat.delta"
    turn: str
    data: DeltaData

    @classmethod
    def of(cls, turn: str, text: str) -> Self:
        """Порция `text` ответа хода `turn`."""
        return cls(turn=turn, data=DeltaData(text=text))


class AvatarEmotion(_Model):
    """Ядро → UI: сменить выражение аватара."""

    v: Version = PROTOCOL_VERSION
    type: Literal["avatar.emotion"] = "avatar.emotion"
    turn: str
    data: EmotionData

    @classmethod
    def of(cls, turn: str, emotion: Emotion, intensity: float = 1.0) -> Self:
        """Эмоция `emotion` в ходе `turn`."""
        return cls(turn=turn, data=EmotionData(emotion=emotion, intensity=intensity))


class TurnFinishedMessage(_Model):
    """Ядро → UI: ответ закончен полностью."""

    v: Version = PROTOCOL_VERSION
    type: Literal["turn.finished"] = "turn.finished"
    turn: str
    data: EmptyData

    @classmethod
    def of(cls, turn: str) -> Self:
        """Ход `turn` завершён."""
        return cls(turn=turn, data=EmptyData())


class TurnCancelledMessage(_Model):
    """Ядро → UI: ход прерван — UI сбрасывает аудиобуфер."""

    v: Version = PROTOCOL_VERSION
    type: Literal["turn.cancelled"] = "turn.cancelled"
    turn: str
    data: CancelledData

    @classmethod
    def of(cls, turn: str, reason: CancelReason, message: str) -> Self:
        """Ход `turn` прерван по `reason`."""
        return cls(turn=turn, data=CancelledData(reason=reason, message=message))


class MetricsSpan(_Model):
    """Ядро → UI: замер стадии; `turn` — None вне хода (прогрев)."""

    v: Version = PROTOCOL_VERSION
    type: Literal["metrics.span"] = "metrics.span"
    turn: str | None
    data: SpanData

    @classmethod
    def of(cls, turn: str | None, name: str, ms: float) -> Self:
        """Замер `name` длительностью `ms`."""
        return cls(turn=turn, data=SpanData(name=name, ms=ms))


class Status(_Model):
    """Ядро → UI: состояние бэкенда (вне хода)."""

    v: Version = PROTOCOL_VERSION
    type: Literal["status"] = "status"
    data: StatusData

    @classmethod
    def of(cls, component: Component, state: BackendState) -> Self:
        """Бэкенд `component` перешёл в `state`."""
        return cls(data=StatusData(component=component, state=state))


class InputBargeIn(_Model):
    """Ядро → UI: пользователь заговорил — оборвать голос витюбера сразу (Этап 11)."""

    v: Version = PROTOCOL_VERSION
    type: Literal["input.barge_in"] = "input.barge_in"
    data: EmptyData = EmptyData()

    @classmethod
    def of(cls) -> Self:
        """Перебивание."""
        return cls()


class InputHypothesis(_Model):
    """Ядро → UI: промежуточный текст фразы пользователя."""

    v: Version = PROTOCOL_VERSION
    type: Literal["input.hypothesis"] = "input.hypothesis"
    data: DeltaData

    @classmethod
    def of(cls, text: str) -> Self:
        """Гипотеза `text`."""
        return cls(data=DeltaData(text=text))


class InputFinal(_Model):
    """Ядро → UI: распознанная фраза — реплика пользователя в чате; за ней начнётся ход."""

    v: Version = PROTOCOL_VERSION
    type: Literal["input.final"] = "input.final"
    data: DeltaData

    @classmethod
    def of(cls, text: str) -> Self:
        """Фраза `text`."""
        return cls(data=DeltaData(text=text))


class ErrorMessage(_Model):
    """Ядро → UI: ошибка; `turn` — None, если не относится к ходу (битое сообщение)."""

    v: Version = PROTOCOL_VERSION
    type: Literal["error"] = "error"
    turn: str | None
    data: ErrorData

    @classmethod
    def of(cls, turn: str | None, code: ErrorCode, message: str) -> Self:
        """Ошибка `code` с текстом `message`."""
        return cls(turn=turn, data=ErrorData(code=code, message=message))


type OutboundMessage = Annotated[
    TurnStartedMessage
    | ChatDelta
    | AvatarEmotion
    | TurnFinishedMessage
    | TurnCancelledMessage
    | MetricsSpan
    | Status
    | InputBargeIn
    | InputHypothesis
    | InputFinal
    | ErrorMessage,
    Field(discriminator="type"),
]
