"""Общие механизмы ядра: шина событий, реестр, телеметрия, конфиг, логи."""

from vtuber.kernel.bus import EventBus, Handler
from vtuber.kernel.config import ConfigFiles, ConfigSection, load_config
from vtuber.kernel.context import current_turn, turn_context
from vtuber.kernel.logging import LoggingConfig, configure_logging, get_logger
from vtuber.kernel.registry import Registry
from vtuber.kernel.telemetry import (
    MAX_PENDING_METRICS,
    Span,
    Telemetry,
    TelemetryConfig,
    TraceWriter,
)

__all__ = [
    "MAX_PENDING_METRICS",
    "ConfigFiles",
    "ConfigSection",
    "EventBus",
    "Handler",
    "LoggingConfig",
    "Registry",
    "Span",
    "Telemetry",
    "TelemetryConfig",
    "TraceWriter",
    "configure_logging",
    "current_turn",
    "get_logger",
    "load_config",
    "turn_context",
]
