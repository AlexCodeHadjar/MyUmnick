"""Иерархия доменных ошибок: адаптеры переводят в неё чужие исключения (R-43)."""


class VtuberError(Exception):
    """Базовая ошибка приложения; сообщение говорит, что делать (R-45)."""


class BackendUnavailable(VtuberError):
    """Бэкенд не отвечает или не загружен."""


class LLMUnavailable(BackendUnavailable):
    """LLM-сервер недоступен."""


class ResourceUnavailable(VtuberError):
    """Модели не хватило видеопамяти или она не загрузилась (ADR-0017); диалог не страдает."""


class SetupFailed(VtuberError):
    """Мастер первого запуска не смог поставить компонент; текст показывается пользователю."""


class TTSUnavailable(BackendUnavailable):
    """Движок синтеза речи недоступен."""


class STTUnavailable(BackendUnavailable):
    """Распознавание речи или детектор недоступны: голосовой ввод молчит, чат работает."""


class MemoryUnavailable(BackendUnavailable):
    """Долговременная память недоступна (модель эмбеддингов или хранилище) — ход идёт без неё."""


class GenerationFailed(VtuberError):
    """Бэкенд ответил, но генерация сорвалась посреди хода."""


class ProtocolError(VtuberError):
    """Сообщение от UI не соответствует протоколу."""


class ConfigError(VtuberError):
    """Конфигурация не читается или не проходит проверку; приложение не стартует."""


class TurnStateError(VtuberError):
    """Недопустимый переход состояния хода — ошибка в логике сервиса, а не во внешнем мире."""
