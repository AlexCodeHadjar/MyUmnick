"""Режиссёр: на что отвечать и когда; ведущий главнее в любой момент."""

import asyncio
import time
from collections.abc import AsyncGenerator, Callable, Mapping
from typing import Final, Protocol

from vtuber.domain import IncomingMessage
from vtuber_stream_chat import EVENT_SOURCE, ChatQueue, RateLimiter

SET_SCENE: Final = "SetCurrentProgramScene"
SET_TEXT: Final = "SetInputSettings"


class Stage(Protocol):
    """Что зрители видят на сцене."""

    async def live(self) -> None:
        """Режиссёр работает."""

    async def paused(self) -> None:
        """Ведущий поставил паузу."""

    async def question(self, message: IncomingMessage) -> None:
        """Витюбер отвечает на это сообщение."""


class ObsRequests(Protocol):
    """Часть клиента OBS, которая нужна сцене."""

    async def request(self, request_type: str, data: Mapping[str, object]) -> None:
        """Отправить запрос в OBS."""


class ObsStage:
    """Сцена в OBS: пустое имя сцены или источника — этого действия просто нет."""

    def __init__(self, client: ObsRequests, scenes: tuple[str, str], question_input: str) -> None:
        self._client = client
        self._live_scene, self._paused_scene = scenes
        self._question_input = question_input

    async def live(self) -> None:
        """Сцена эфира."""
        await self._scene(self._live_scene)

    async def paused(self) -> None:
        """Сцена паузы; вопрос больше не актуален."""
        await self._scene(self._paused_scene)
        await self._show_question("")

    async def question(self, message: IncomingMessage) -> None:
        """Показать, на чьё сообщение витюбер отвечает."""
        await self._show_question(f"{message.author}: {message.text}")

    async def _scene(self, name: str) -> None:
        if name:
            await self._client.request(SET_SCENE, {"sceneName": name})

    async def _show_question(self, text: str) -> None:
        if self._question_input:
            settings = {"inputName": self._question_input, "inputSettings": {"text": text}}
            await self._client.request(SET_TEXT, settings)


class StreamDirector:
    """Выдаёт реплики ядру, пока нет паузы и ведущий не говорил `host_hold_s` секунд.

    События канала (рейд, подписка) идут раньше сообщений и без фильтра: их текст пишет Twitch.
    """

    def __init__(
        self,
        chat: tuple[ChatQueue, RateLimiter],
        stage: Stage,
        host_hold_s: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._queue, self._limiter = chat
        self._stage = stage
        self._host_hold_s = host_hold_s
        self._clock = clock
        self._unpaused = asyncio.Event()
        self._unpaused.set()
        self._hold_until = 0.0

    @property
    def is_paused(self) -> bool:
        """Стоит ли пауза ведущего."""
        return not self._unpaused.is_set()

    def add(self, message: IncomingMessage) -> None:
        """Сообщение из чата или событие канала."""
        if message.source == EVENT_SOURCE:
            self._queue.add_urgent(message)
        else:
            self._queue.add(message)

    def host_spoke(self) -> None:
        """Ведущий говорит сам: дать ему договорить и не вклиниваться сразу после ответа."""
        self._hold_until = self._clock() + self._host_hold_s

    async def pause(self) -> None:
        """Новых ответов зрителям нет, пока ведущий не снимет паузу."""
        self._unpaused.clear()
        await self._stage.paused()

    async def resume(self) -> None:
        """Снять паузу."""
        self._unpaused.set()
        await self._stage.live()

    async def selected(self) -> AsyncGenerator[IncomingMessage]:
        """Следующая реплика; запрашивается ядром, когда витюбер договорил."""
        while True:
            await self._ready()
            await self._limiter.wait()
            message = await self._queue.next()
            # Пока ждали сообщение, ведущий мог вмешаться: тогда оно подождёт в очереди.
            if self.is_paused or self._clock() < self._hold_until:
                self._queue.put_back(message)
                continue
            self._limiter.mark()
            await self._stage.question(message)
            yield message

    async def _ready(self) -> None:
        while self.is_paused or (left := self._hold_until - self._clock()) > 0:
            if self.is_paused:
                await self._unpaused.wait()
            else:
                await asyncio.sleep(left)
