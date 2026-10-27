"""Структурные JSON-логи на structlog; turn_id добавляет `kernel.context.turn_context`."""

from pathlib import Path
from typing import Literal, TextIO, cast

import structlog
from structlog.typing import FilteringBoundLogger

from vtuber.kernel.config import ConfigSection

type LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


class LoggingConfig(ConfigSection):
    """Секция `[logging]`; `file` открывает bootstrap (относительно корня проекта)."""

    level: LogLevel
    file: Path


def configure_logging(cfg: LoggingConfig, stream: TextIO) -> None:
    """Настраивает structlog: одна JSON-строка на событие в `stream`.

    Вызывается один раз при старте из bootstrap, который владеет потоком (файлом).
    События ниже `cfg.level` отсекаются до форматирования — DEBUG-вызовы почти бесплатны (T-15).
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(cfg.level),
        logger_factory=structlog.WriteLoggerFactory(file=stream),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> FilteringBoundLogger:
    """Логгер модуля; имя попадает в поле `module` каждого события.

    Можно брать на уровне модуля, до `configure_logging`: имя — начальное значение ленивого
    прокси, настройка подхватывается при первом событии. (`.bind()` у прокси, наоборот,
    зафиксировал бы настройку по умолчанию в момент импорта.)
    """
    return cast("FilteringBoundLogger", structlog.get_logger(module=name))
