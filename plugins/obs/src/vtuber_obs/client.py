"""Клиент OBS WebSocket 5: вход, запросы без ожидания ответа, переподключение."""

import asyncio
import base64
import hashlib
import json
from collections.abc import Mapping
from itertools import count
from typing import Final

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed

from vtuber.kernel import get_logger

RPC_VERSION: Final = 1
OP_HELLO: Final = 0
OP_IDENTIFY: Final = 1
OP_IDENTIFIED: Final = 2
OP_REQUEST: Final = 6
OP_RESPONSE: Final = 7

_log = get_logger(__name__)


def _digest(text: str) -> str:
    return base64.b64encode(hashlib.sha256(text.encode()).digest()).decode()


def auth_string(password: str, salt: str, challenge: str) -> str:
    """Ответ на вызов OBS: base64(sha256(base64(sha256(пароль + соль)) + вызов))."""
    return _digest(_digest(password + salt) + challenge)


def _identify(hello: object, password: str) -> dict[str, object]:
    data: dict[str, object] = {"rpcVersion": RPC_VERSION, "eventSubscriptions": 0}
    if isinstance(hello, dict):
        auth = hello.get("d", {}).get("authentication")
        if auth is not None:
            data["authentication"] = auth_string(password, auth["salt"], auth["challenge"])
    return {"op": OP_IDENTIFY, "d": data}


class ObsClient:
    """Держит соединение с OBS. Нет соединения — запрос теряется: стрим важнее субтитров."""

    def __init__(self, url: str, password: str, reconnect_s: float) -> None:
        self._url = url
        self._password = password
        self._reconnect_s = reconnect_s
        self._ws: ClientConnection | None = None
        self._ids = count(1)

    async def run(self) -> None:
        """Подключается и переподключается, пока задачу не отменят."""
        while True:
            try:
                await self._session()
            except (OSError, ConnectionClosed, TimeoutError, ValueError, KeyError) as exc:
                _log.warning("obs.disconnected", problem=str(exc))
            finally:
                self._ws = None
            await asyncio.sleep(self._reconnect_s)

    async def request(self, request_type: str, data: Mapping[str, object]) -> None:
        """Отправляет запрос; ошибку OBS покажет лог, ход её не ждёт."""
        ws = self._ws
        if ws is None:
            return
        payload = {
            "requestType": request_type,
            "requestId": str(next(self._ids)),
            "requestData": dict(data),
        }
        try:
            await ws.send(json.dumps({"op": OP_REQUEST, "d": payload}))
        except ConnectionClosed:
            _log.info("obs.request_lost", request=request_type)

    async def _session(self) -> None:
        async with connect(self._url) as ws:
            await ws.send(json.dumps(_identify(json.loads(await ws.recv()), self._password)))
            if json.loads(await ws.recv()).get("op") != OP_IDENTIFIED:
                msg = "OBS не подтвердил вход"
                raise ValueError(msg)
            self._ws = ws
            _log.info("obs.connected")
            async for frame in ws:
                _log_failure(json.loads(frame))


def _log_failure(message: dict[str, object]) -> None:
    body = message.get("d")
    if message.get("op") != OP_RESPONSE or not isinstance(body, dict):
        return
    status = body.get("requestStatus", {})
    if not status.get("result", True):
        # Обычно это опечатка в имени сцены или источника.
        _log.warning("obs.request_failed", request=body.get("requestType"), status=status)
