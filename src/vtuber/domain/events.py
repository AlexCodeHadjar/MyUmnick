"""События шины управления: что произошло в ядре (горячий путь идёт очередями, T-15)."""

from dataclasses import dataclass
from enum import StrEnum

from vtuber.domain.dialogue import TurnId
from vtuber.domain.emotion import Emotion


class CancelReason(StrEnum):
    """Почему ход прерван."""

    USER_STOP = "user_stop"
    NEW_MESSAGE = "new_message"
    ERROR = "error"


class Component(StrEnum):
    """Бэкенд, о состоянии которого сообщается в UI."""

    LLM = "llm"
    TTS = "tts"


class BackendState(StrEnum):
    """Состояние бэкенда для статус-бара UI."""

    LOADING = "loading"
    READY = "ready"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class TurnStarted:
    """Ход начат: аватар сразу показывает «думаю» (T-17)."""

    turn_id: TurnId


@dataclass(frozen=True, slots=True)
class TurnFinished:
    """Ход завершён полностью."""

    turn_id: TurnId


@dataclass(frozen=True, slots=True)
class TurnCancelled:
    """Ход прерван; UI сбрасывает аудиобуфер."""

    turn_id: TurnId
    reason: CancelReason


@dataclass(frozen=True, slots=True)
class EmotionChanged:
    """В ответе встретился тег эмоции."""

    turn_id: TurnId
    emotion: Emotion


@dataclass(frozen=True, slots=True)
class BackendStatusChanged:
    """Бэкенд загрузился, упал или восстановился."""

    component: Component
    state: BackendState
