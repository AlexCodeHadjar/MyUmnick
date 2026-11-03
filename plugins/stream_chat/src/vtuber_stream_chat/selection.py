"""Что из чата стрима дойдёт до витюбера: фильтры, очередь, выбор, лимит частоты."""

import asyncio
import re
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Final

from pydantic import Field

from vtuber.domain import IncomingMessage
from vtuber.kernel import ConfigSection

_LINK: Final = re.compile(r"https?://|www\.|\b[\w-]+\.(?:com|ru|net|org|tv|gg)\b", re.IGNORECASE)
_COMMAND_PREFIX: Final = "!"

_PRIORITY_MENTION: Final = 2
_PRIORITY_QUESTION: Final = 1
_PRIORITY_OTHER: Final = 0


class ChatFilterConfig(ConfigSection):
    """Какие сообщения отбрасываются сразу."""

    min_chars: int = Field(default=2, ge=1)
    max_chars: int = Field(default=300, ge=1)
    blocked_words: tuple[str, ...] = ()
    ignored_authors: tuple[str, ...] = ()


class ChatQueueConfig(ConfigSection):
    """Очередь: `mention_names` — обращения к витюберу, они выбираются первыми."""

    max_size: int = Field(default=50, ge=1)
    max_age_s: float = Field(default=60.0, gt=0)
    mention_names: tuple[str, ...] = ()


def passes_filter(message: IncomingMessage, cfg: ChatFilterConfig) -> bool:
    """Ссылки и команды ботов не озвучиваются; остальное — по длине, словам и авторам."""
    text = message.text.strip()
    lowered = text.casefold()
    return (
        cfg.min_chars <= len(text) <= cfg.max_chars
        and not text.startswith(_COMMAND_PREFIX)
        and _LINK.search(text) is None
        and not any(word.casefold() in lowered for word in cfg.blocked_words)
        and message.author.casefold() not in {name.casefold() for name in cfg.ignored_authors}
    )


@dataclass(frozen=True, slots=True)
class _Queued:
    message: IncomingMessage
    at: float


class ChatQueue:
    """Ограниченная очередь: при наплыве теряются старые, устаревшие не озвучиваются."""

    def __init__(
        self,
        cfg: ChatQueueConfig,
        chat_filter: ChatFilterConfig,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._cfg = cfg
        self._filter = chat_filter
        self._clock = clock
        self._items: deque[_Queued] = deque(maxlen=cfg.max_size)
        self._arrived = asyncio.Event()

    def add(self, message: IncomingMessage) -> None:
        """Принять сообщение, если оно проходит фильтры и не повторяет уже ждущее."""
        if not passes_filter(message, self._filter) or self._is_repeat(message):
            return
        self._items.append(_Queued(message, self._clock()))
        self._arrived.set()

    def pick(self) -> IncomingMessage | None:
        """Лучшее из свежих: обращение, затем вопрос; при равенстве — самое новое."""
        oldest_allowed = self._clock() - self._cfg.max_age_s
        fresh = [item for item in self._items if item.at >= oldest_allowed]
        self._items.clear()
        if not fresh:
            self._arrived.clear()
            return None
        best = max(reversed(fresh), key=lambda item: self._priority(item.message))
        self._items.extend(item for item in fresh if item is not best)
        return best.message

    async def next(self) -> IncomingMessage:
        """Ждёт, пока появится что выбрать."""
        while (message := self.pick()) is None:
            await self._arrived.wait()
        return message

    def _is_repeat(self, message: IncomingMessage) -> bool:
        text = message.text.strip().casefold()
        return any(item.message.text.strip().casefold() == text for item in self._items)

    def _priority(self, message: IncomingMessage) -> int:
        lowered = message.text.casefold()
        if any(name.casefold() in lowered for name in self._cfg.mention_names):
            return _PRIORITY_MENTION
        return _PRIORITY_QUESTION if "?" in lowered else _PRIORITY_OTHER


class RateLimiter:
    """Не чаще одного ответа за `min_interval_s`, сколько бы ни писали зрители."""

    def __init__(
        self,
        min_interval_s: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._min_interval_s = min_interval_s
        self._clock = clock
        self._sleep = sleep
        self._last: float | None = None

    async def wait(self) -> None:
        """Дождаться права на следующий ответ."""
        if self._last is not None:
            left = self._last + self._min_interval_s - self._clock()
            if left > 0:
                await self._sleep(left)

    def mark(self) -> None:
        """Ответ начат: отсчёт интервала идёт от этого момента."""
        self._last = self._clock()
