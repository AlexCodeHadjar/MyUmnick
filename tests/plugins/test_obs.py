import asyncio
import base64
import hashlib
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from websockets.asyncio.server import ServerConnection, serve

from vtuber.domain import (
    CancelReason,
    Emotion,
    EmotionChanged,
    PhraseVoiced,
    TurnCancelled,
    TurnId,
)
from vtuber.kernel import EventBus, PluginContext
from vtuber_obs import ObsPlugin, auth_string

PASSWORD = "секрет"  # noqa: S105 — значение для фейкового сервера
SALT = "соль"
CHALLENGE = "вызов"
TURN = TurnId(1)


def _hash(text: str) -> str:
    return base64.b64encode(hashlib.sha256(text.encode()).digest()).decode()


class _FakeObs:
    """Сервер OBS WebSocket 5: проверяет вход и запоминает запросы."""

    def __init__(self) -> None:
        self.identify: dict[str, object] = {}
        self.requests: list[dict[str, object]] = []
        self.ready = asyncio.Event()

    async def handler(self, ws: ServerConnection) -> None:
        auth = {"salt": SALT, "challenge": CHALLENGE}
        await ws.send(json.dumps({"op": 0, "d": {"rpcVersion": 1, "authentication": auth}}))
        self.identify = json.loads(await ws.recv())["d"]
        await ws.send(json.dumps({"op": 2, "d": {"negotiatedRpcVersion": 1}}))
        self.ready.set()
        async for frame in ws:
            self.requests.append(json.loads(frame)["d"])

    def subtitles(self) -> list[object]:
        return [
            r["requestData"]["inputSettings"]["text"]  # type: ignore[index]
            for r in self.requests
            if r["requestType"] == "SetInputSettings"
        ]


@asynccontextmanager
async def _plugin(**settings: object) -> AsyncIterator[tuple[EventBus, _FakeObs]]:
    obs = _FakeObs()
    async with serve(obs.handler, "127.0.0.1", 0) as server:
        port = next(iter(server.sockets)).getsockname()[1]
        bus = EventBus()
        cfg = {"url": f"ws://127.0.0.1:{port}", "password": PASSWORD, **settings}
        ctx = PluginContext("obs", bus, cfg)
        plugin = ObsPlugin()
        await plugin.setup(ctx)
        pump = asyncio.create_task(ctx.run())
        await asyncio.wait_for(obs.ready.wait(), 5)
        try:
            yield bus, obs
        finally:
            pump.cancel()
            await plugin.shutdown()


def test_auth_string_matches_obs_protocol() -> None:
    expected = _hash(_hash(PASSWORD + SALT) + CHALLENGE)
    assert auth_string(PASSWORD, SALT, CHALLENGE) == expected


async def test_identifies_with_password() -> None:
    async with _plugin() as (_, obs):
        assert obs.identify["authentication"] == auth_string(PASSWORD, SALT, CHALLENGE)


async def test_subtitle_appears_when_phrase_sounds_and_clears_after_it() -> None:
    async with _plugin(subtitle_input="Субтитры") as (bus, obs):
        await bus.publish(PhraseVoiced("Первая.", starts_in_s=0.05, duration_s=0.05))
        await asyncio.sleep(0.02)
        assert obs.subtitles() == []  # звук ещё не начался
        await asyncio.sleep(0.05)
        assert obs.subtitles() == ["Первая."]
        await asyncio.sleep(0.08)
        assert obs.subtitles() == ["Первая.", ""]


async def test_next_phrase_is_not_erased_by_previous_one() -> None:
    async with _plugin(subtitle_input="Субтитры") as (bus, obs):
        await bus.publish(PhraseVoiced("Первая.", starts_in_s=0.0, duration_s=0.05))
        await bus.publish(PhraseVoiced("Вторая.", starts_in_s=0.05, duration_s=0.05))
        await asyncio.sleep(0.15)
        assert obs.subtitles() == ["Первая.", "Вторая.", ""]


async def test_cancel_clears_subtitle_at_once() -> None:
    async with _plugin(subtitle_input="Субтитры") as (bus, obs):
        await bus.publish(PhraseVoiced("Долгая.", starts_in_s=0.0, duration_s=5.0))
        await asyncio.sleep(0.03)
        await bus.publish(TurnCancelled(TURN, CancelReason.USER_STOP))
        await asyncio.sleep(0.03)
        assert obs.subtitles() == ["Долгая.", ""]


async def test_scene_changes_only_for_mapped_emotion() -> None:
    async with _plugin(scenes={"happy": "Весёлая"}) as (bus, obs):
        await bus.publish(EmotionChanged(TURN, Emotion.SAD))
        await bus.publish(EmotionChanged(TURN, Emotion.HAPPY))
        await asyncio.sleep(0.03)
        assert [r["requestData"] for r in obs.requests] == [{"sceneName": "Весёлая"}]


async def test_works_without_obs_running() -> None:
    bus = EventBus()
    ctx = PluginContext(
        "obs", bus, {"url": "ws://127.0.0.1:9", "reconnect_s": 0.01, "subtitle_input": "С"}
    )
    plugin = ObsPlugin()
    await plugin.setup(ctx)
    pump = asyncio.create_task(ctx.run())
    await bus.publish(PhraseVoiced("Текст.", starts_in_s=0.0, duration_s=0.0))
    await asyncio.sleep(0.03)
    pump.cancel()
    await plugin.shutdown()
