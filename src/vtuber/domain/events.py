"""События шины управления: что произошло в ядре (горячий путь идёт очередями, T-15)."""

from dataclasses import dataclass
from enum import StrEnum

from vtuber.domain.dialogue import Message, Turn, TurnId
from vtuber.domain.emotion import Emotion


class CancelReason(StrEnum):
    """Почему ход прерван."""

    USER_STOP = "user_stop"
    NEW_MESSAGE = "new_message"
    BARGE_IN = "barge_in"
    ERROR = "error"


class Component(StrEnum):
    """Бэкенд, о состоянии которого сообщается в UI."""

    LLM = "llm"
    TTS = "tts"
    STT = "stt"


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
class TurnRemembered:
    """Ход записан в историю; `dropped` — сообщения, отрезанные из неё при этом (T-04).

    Для фоновой памяти (Этап 10): факты из хода и резюме отрезанного — задачами в простое.
    """

    turn: Turn
    dropped: tuple[Message, ...]


@dataclass(frozen=True, slots=True)
class TurnFinished:
    """Ход завершён полностью."""

    turn_id: TurnId


@dataclass(frozen=True, slots=True)
class TurnCancelled:
    """Ход прерван; UI сбрасывает аудиобуфер. `message` — что сказать пользователю при ошибке."""

    turn_id: TurnId
    reason: CancelReason
    message: str = ""


@dataclass(frozen=True, slots=True)
class EmotionChanged:
    """В ответе встретился тег эмоции."""

    turn_id: TurnId
    emotion: Emotion


@dataclass(frozen=True, slots=True)
class PhraseVoiced:
    """Фраза озвучена: зазвучит через `starts_in_s` и продлится `duration_s` (субтитры, Этап 12).

    Ответ готов намного раньше, чем произнесён, поэтому показать фразу вовремя можно только так.
    Время — оценка по отданному звуку: задержка сети и плеера UI не учтены.
    """

    text: str
    starts_in_s: float
    duration_s: float


@dataclass(frozen=True, slots=True)
class BackendNotice:
    """Сообщение пользователю о компоненте: упал, поднимается, снова работает (S-17.1)."""

    component: Component
    text: str


@dataclass(frozen=True, slots=True)
class ViewerBlocked:
    """Реплика зрителя похожа на атаку и не дошла до модели; ведущий видит это в UI (FR-31)."""

    author: str
    text: str


@dataclass(frozen=True, slots=True)
class MetricRecorded:
    """Замер стадии хода; `turn_id` — None, если замер вне хода (например, прогрев)."""

    name: str
    duration_ns: int
    turn_id: TurnId | None


@dataclass(frozen=True, slots=True)
class BackendStatusChanged:
    """Бэкенд загрузился, упал или восстановился."""

    component: Component
    state: BackendState
