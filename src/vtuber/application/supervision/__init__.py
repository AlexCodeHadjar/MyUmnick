"""Самовосстановление (S-17.1, ADR-0021): наблюдатель за компонентами и обёртки голоса и слуха."""

from vtuber.application.supervision.supervisor import Supervised, Supervisor, SupervisorConfig
from vtuber.application.supervision.watched import FailureFlag, WatchedSTT, WatchedTTS

__all__ = [
    "FailureFlag",
    "Supervised",
    "Supervisor",
    "SupervisorConfig",
    "WatchedSTT",
    "WatchedTTS",
]
