"""Протокол UI ↔ Ядро v1: модели сообщений — единственный источник схемы (TS-типы, docs)."""

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field

from vtuber.domain import BackendState, CancelReason, Component, Emotion, TurnId
from vtuber.gateway.protocol_base import PROTOCOL_VERSION, EmptyData, ProtocolModel, Version
from vtuber.gateway.protocol_extras import (
    BackendNoticeMessage,
    ResourcesMessage,
    ResourcesWatch,
    SetupCancel,
    SetupFinished,
    SetupInstall,
    SetupProgress,
    SetupStateMessage,
    ViewerBlockedMessage,
)
from vtuber.gateway.protocol_memory import (
    MemoryErase,
    MemoryErased,
    MemoryFactDelete,
    MemoryFacts,
    MemoryFactSave,
    MemoryList,
    PrivacySet,
    PrivacyState,
)


def turn_ref(turn_id: TurnId) -> str:
    """Номер хода в JSON-сообщениях: `t-000042` (в аудиокадре — uint64)."""
    return f"t-{turn_id:06d}"


class ErrorCode(StrEnum):
    """Что пошло не так — UI выбирает реакцию по коду, текст показывает пользователю."""

    BAD_MESSAGE = "bad_message"
    LLM_UNAVAILABLE = "llm_unavailable"
    GENERATION_FAILED = "generation_failed"
    INTERNAL = "internal"


class SendData(ProtocolModel):
    """Реплика пользователя."""

    text: str = Field(min_length=1)


class TypingData(ProtocolModel):
    """Черновик реплики, пока пользователь печатает; пустой — поле очищено."""

    text: str


class DeltaData(ProtocolModel):
    """Порция текста ответа."""

    text: str


class EmotionData(ProtocolModel):
    """Эмоция аватара; `intensity` 0…1 (затухание — Этап 8)."""

    emotion: Emotion
    intensity: float = Field(ge=0, le=1)


class CancelledData(ProtocolModel):
    """Почему ход прерван; `message` — текст ошибки при `reason == "error"`."""

    reason: CancelReason
    message: str


class SpanData(ProtocolModel):
    """Замер стадии хода для панели метрик (FR-15)."""

    name: str
    ms: float


class StatusData(ProtocolModel):
    """Состояние бэкенда для статус-бара."""

    component: Component
    state: BackendState


class ErrorData(ProtocolModel):
    """Ошибка для пользователя."""

    code: ErrorCode
    message: str


class ChatSend(ProtocolModel):
    """UI → Ядро: новая реплика; прерывает текущий ход."""

    v: Version
    type: Literal["chat.send"]
    data: SendData


class ChatCancel(ProtocolModel):
    """UI → Ядро: остановить ответ."""

    v: Version
    type: Literal["chat.cancel"]
    data: EmptyData


class InputTyping(ProtocolModel):
    """UI → Ядро: черновик реплики (с дебаунсом ~300 мс) — прогрев кэша LLM, T-05."""

    v: Version
    type: Literal["input.typing"]
    data: TypingData


type InboundMessage = Annotated[
    ChatSend
    | ChatCancel
    | InputTyping
    | ResourcesWatch
    | SetupInstall
    | SetupCancel
    | PrivacySet
    | MemoryErase
    | MemoryList
    | MemoryFactSave
    | MemoryFactDelete,
    Field(discriminator="type"),
]


class TurnStartedMessage(ProtocolModel):
    """Ядро → UI: ход начат — аватар «думает» (T-17)."""

    v: Version = PROTOCOL_VERSION
    type: Literal["turn.started"] = "turn.started"
    turn: str
    data: EmptyData

    @classmethod
    def of(cls, turn: str) -> Self:
        """Сообщение о начале хода `turn`."""
        return cls(turn=turn, data=EmptyData())


class ChatDelta(ProtocolModel):
    """Ядро → UI: порция текста ответа."""

    v: Version = PROTOCOL_VERSION
    type: Literal["chat.delta"] = "chat.delta"
    turn: str
    data: DeltaData

    @classmethod
    def of(cls, turn: str, text: str) -> Self:
        """Порция `text` ответа хода `turn`."""
        return cls(turn=turn, data=DeltaData(text=text))


class AvatarEmotion(ProtocolModel):
    """Ядро → UI: сменить выражение аватара."""

    v: Version = PROTOCOL_VERSION
    type: Literal["avatar.emotion"] = "avatar.emotion"
    turn: str
    data: EmotionData

    @classmethod
    def of(cls, turn: str, emotion: Emotion, intensity: float = 1.0) -> Self:
        """Эмоция `emotion` в ходе `turn`."""
        return cls(turn=turn, data=EmotionData(emotion=emotion, intensity=intensity))


class TurnFinishedMessage(ProtocolModel):
    """Ядро → UI: ответ закончен полностью."""

    v: Version = PROTOCOL_VERSION
    type: Literal["turn.finished"] = "turn.finished"
    turn: str
    data: EmptyData

    @classmethod
    def of(cls, turn: str) -> Self:
        """Ход `turn` завершён."""
        return cls(turn=turn, data=EmptyData())


class TurnCancelledMessage(ProtocolModel):
    """Ядро → UI: ход прерван — UI сбрасывает аудиобуфер."""

    v: Version = PROTOCOL_VERSION
    type: Literal["turn.cancelled"] = "turn.cancelled"
    turn: str
    data: CancelledData

    @classmethod
    def of(cls, turn: str, reason: CancelReason, message: str) -> Self:
        """Ход `turn` прерван по `reason`."""
        return cls(turn=turn, data=CancelledData(reason=reason, message=message))


class MetricsSpan(ProtocolModel):
    """Ядро → UI: замер стадии; `turn` — None вне хода (прогрев)."""

    v: Version = PROTOCOL_VERSION
    type: Literal["metrics.span"] = "metrics.span"
    turn: str | None
    data: SpanData

    @classmethod
    def of(cls, turn: str | None, name: str, ms: float) -> Self:
        """Замер `name` длительностью `ms`."""
        return cls(turn=turn, data=SpanData(name=name, ms=ms))


class Status(ProtocolModel):
    """Ядро → UI: состояние бэкенда (вне хода)."""

    v: Version = PROTOCOL_VERSION
    type: Literal["status"] = "status"
    data: StatusData

    @classmethod
    def of(cls, component: Component, state: BackendState) -> Self:
        """Бэкенд `component` перешёл в `state`."""
        return cls(data=StatusData(component=component, state=state))


class InputBargeIn(ProtocolModel):
    """Ядро → UI: пользователь заговорил — оборвать голос витюбера сразу (Этап 11)."""

    v: Version = PROTOCOL_VERSION
    type: Literal["input.barge_in"] = "input.barge_in"
    data: EmptyData = EmptyData()

    @classmethod
    def of(cls) -> Self:
        """Перебивание."""
        return cls()


class InputHypothesis(ProtocolModel):
    """Ядро → UI: промежуточный текст фразы пользователя."""

    v: Version = PROTOCOL_VERSION
    type: Literal["input.hypothesis"] = "input.hypothesis"
    data: DeltaData

    @classmethod
    def of(cls, text: str) -> Self:
        """Гипотеза `text`."""
        return cls(data=DeltaData(text=text))


class InputFinal(ProtocolModel):
    """Ядро → UI: распознанная фраза — реплика пользователя в чате; за ней начнётся ход."""

    v: Version = PROTOCOL_VERSION
    type: Literal["input.final"] = "input.final"
    data: DeltaData

    @classmethod
    def of(cls, text: str) -> Self:
        """Фраза `text`."""
        return cls(data=DeltaData(text=text))


class ErrorMessage(ProtocolModel):
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
    | ResourcesMessage
    | SetupStateMessage
    | SetupProgress
    | SetupFinished
    | ViewerBlockedMessage
    | BackendNoticeMessage
    | PrivacyState
    | MemoryErased
    | MemoryFacts
    | ErrorMessage,
    Field(discriminator="type"),
]
