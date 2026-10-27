"""Структурные JSON-логи на structlog с turn_id текущего хода через contextvars."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Literal, TextIO, cast

import structlog
from structlog.typing import FilteringBoundLogger

from vtuber.domain import TurnId
from vtuber.kernel.config import ConfigSection

type LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


class LoggingConfig(ConfigSection):
    """Секция `[logging]`."""

    level: LogLevel


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
    """Логгер модуля; имя попадает в поле `logger` каждого события."""
    return cast("FilteringBoundLogger", structlog.get_logger().bind(logger=name))


@contextmanager
def turn_context(turn_id: TurnId) -> Iterator[None]:
    """Все события внутри блока несут `turn_id`, включая задачи asyncio, созданные в нём."""
    with structlog.contextvars.bound_contextvars(turn_id=turn_id):
        yield
