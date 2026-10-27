"""Структурные JSON-логи на structlog; turn_id добавляет `kernel.context.turn_context`."""

from collections.abc import Iterator
from contextlib import contextmanager
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

    События ниже `cfg.level` отсекаются до форматирования (T-15). Логгеры не кэшируются:
    кэш навсегда привязал бы логгеры модулей к первому потоку — после его закрытия или смены
    настройки они писали бы в закрытый файл. Логи — события жизненного цикла, не горячий путь.
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
        cache_logger_on_first_use=False,
    )


@contextmanager
def logging_to(cfg: LoggingConfig, stream: TextIO) -> Iterator[None]:
    """Логи идут в `stream` на время блока; на выходе — настройка по умолчанию.

    Сброс происходит до закрытия потока владельцем, поэтому поздние события не пишут в
    закрытый файл.
    """
    configure_logging(cfg, stream)
    try:
        yield
    finally:
        structlog.reset_defaults()


def get_logger(name: str) -> FilteringBoundLogger:
    """Логгер модуля; имя попадает в поле `module` каждого события.

    Можно брать на уровне модуля, до `configure_logging`: имя — начальное значение ленивого
    прокси, настройка подхватывается при каждом событии. (`.bind()` у прокси, наоборот,
    зафиксировал бы настройку по умолчанию в момент импорта.)
    """
    return cast("FilteringBoundLogger", structlog.get_logger(module=name))
