"""Плагин OBS: субтитры текущей фразы и смена сцены по эмоции (FR-14, S-12.3)."""

import asyncio

from pydantic import Field

from vtuber.domain import EmotionChanged, PhraseVoiced, TurnCancelled, TurnStarted
from vtuber.kernel import ConfigSection, PluginContext
from vtuber_obs.client import ObsClient, auth_string

__all__ = ["ObsClient", "ObsConfig", "ObsPlugin", "auth_string"]


class ObsConfig(ConfigSection):
    """Секция `[plugins.settings.obs]`: `scenes` — эмоция → сцена; пусто — сцена не меняется."""

    url: str = "ws://127.0.0.1:4455"
    password: str = ""
    reconnect_s: float = Field(default=5.0, gt=0)
    subtitle_input: str = ""
    scenes: dict[str, str] = Field(default_factory=dict)


class ObsPlugin:
    """Показывает фразу, когда она звучит: ответ готов намного раньше, чем произнесён."""

    name = "obs"

    def __init__(self) -> None:
        self._cfg: ObsConfig | None = None
        self._client: ObsClient | None = None
        self._connection: asyncio.Task[None] | None = None
        self._timers: set[asyncio.Task[None]] = set()

    async def setup(self, ctx: PluginContext) -> None:
        """Подключиться к OBS в фоне и подписаться: без OBS приложение работает как обычно."""
        cfg = ctx.settings(ObsConfig)
        self._cfg = cfg
        self._client = ObsClient(cfg.url, cfg.password, cfg.reconnect_s)
        self._connection = asyncio.create_task(self._client.run())
        ctx.subscribe(PhraseVoiced, self._on_phrase)
        ctx.subscribe(EmotionChanged, self._on_emotion)
        ctx.subscribe(TurnStarted, self._on_new_turn)
        ctx.subscribe(TurnCancelled, self._on_cancelled)

    async def shutdown(self) -> None:
        """Убрать таймеры и закрыть соединение."""
        self._stop_timers()
        if self._connection is not None:
            self._connection.cancel()
            await asyncio.wait({self._connection})

    async def _on_phrase(self, event: PhraseVoiced) -> None:
        if self._cfg is None or not self._cfg.subtitle_input:
            return
        timer = asyncio.create_task(self._show(event))
        self._timers.add(timer)
        timer.add_done_callback(self._timers.discard)

    async def _show(self, event: PhraseVoiced) -> None:
        await asyncio.sleep(event.starts_in_s)
        await self._subtitle(event.text)
        await asyncio.sleep(event.duration_s)
        # Следующая фраза уже показана поверх этой — стирать только свой текст.
        if not any(t is not asyncio.current_task() and not t.done() for t in self._timers):
            await self._subtitle("")

    async def _on_emotion(self, event: EmotionChanged) -> None:
        if self._cfg is None or self._client is None:
            return
        scene = self._cfg.scenes.get(event.emotion.value)
        if scene is not None:
            await self._client.request("SetCurrentProgramScene", {"sceneName": scene})

    async def _on_new_turn(self, _: TurnStarted) -> None:
        await self._silence()

    async def _on_cancelled(self, _: TurnCancelled) -> None:
        await self._silence()

    async def _silence(self) -> None:
        """Голос прошлого хода оборван: его фраза и таймеры больше не нужны."""
        if self._timers:
            self._stop_timers()
            await self._subtitle("")

    def _stop_timers(self) -> None:
        for timer in tuple(self._timers):
            timer.cancel()

    async def _subtitle(self, text: str) -> None:
        if self._cfg is None or self._client is None:
            return
        settings = {"inputName": self._cfg.subtitle_input, "inputSettings": {"text": text}}
        await self._client.request("SetInputSettings", settings)
