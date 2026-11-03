"""Порт источника реплик: откуда приходят сообщения помимо чата UI (Этап 12)."""

from collections.abc import AsyncGenerator
from typing import Protocol

from vtuber.domain import IncomingMessage


class MessageSource(Protocol):
    """Поток реплик: чат стрима, тестовый фейк. Сам восстанавливает соединение."""

    def messages(self) -> AsyncGenerator[IncomingMessage]:
        """Реплики по мере появления; потребитель закрывает через `aclosing`."""
        ...
