"""Шина управляющих событий. НЕ для горячего пути: токены и аудио идут очередями (T-15)."""

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import cast

from vtuber.kernel.logging import get_logger

type Handler[E] = Callable[[E], Awaitable[None]]

_log = get_logger(__name__)


class EventBus:
    """Доставляет событие подписчикам его точного типа (не подклассов), параллельно.

    Ошибка подписчика логируется и не мешает ни остальным, ни издателю: плагин не уронит ход.
    Отмена `publish` отменяет подписчиков и пролетает дальше (R-38).
    """

    def __init__(self) -> None:
        self._handlers: defaultdict[type[object], list[Handler[object]]] = defaultdict(list)

    def subscribe[E](self, event_type: type[E], handler: Handler[E]) -> None:
        """Подписывает `handler` на события типа `event_type`."""
        # Handler[E] хранится как Handler[object]: publish вызывает его только с событиями типа E.
        self._handlers[event_type].append(cast("Handler[object]", handler))

    async def publish(self, event: object) -> None:
        """Ждёт, пока все подписчики обработают событие."""
        handlers = tuple(self._handlers.get(type(event), ()))
        if not handlers:
            return
        results = await asyncio.gather(
            *(handler(event) for handler in handlers), return_exceptions=True
        )
        for handler, result in zip(handlers, results, strict=True):
            if isinstance(result, Exception):
                _log.error(
                    "bus.handler_failed",
                    event_type=type(event).__name__,
                    handler=repr(handler),
                    exc_info=result,
                )
            elif isinstance(result, BaseException):
                raise result
