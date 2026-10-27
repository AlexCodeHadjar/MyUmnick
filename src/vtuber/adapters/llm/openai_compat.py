"""Адаптер LLMPort для OpenAI-совместимого API (`/v1/chat/completions`, стрим SSE)."""

from collections.abc import AsyncIterator, Sequence
from types import TracebackType
from typing import Final, Self

import httpx

from vtuber.adapters.llm.config import LLMConfig
from vtuber.adapters.llm.sse import SSE_DONE, data_of, delta_text
from vtuber.domain import GenerationFailed, LLMUnavailable, Message
from vtuber.ports import GenerationParams

CHAT_PATH: Final = "/v1/chat/completions"
MODELS_PATH: Final = "/v1/models"
MODEL_LOADING_STATUS: Final = 503
ERROR_BODY_LIMIT: Final = 300
_UNREACHABLE = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)


class OpenAICompatLLM:
    """Стрим ответа по HTTP/SSE; один httpx-клиент на всё время жизни (R-40, ADR-0007).

    Использовать как `async with OpenAICompatLLM(cfg) as llm` — выход закрывает соединения.
    Отмена потребителя закрывает ответ, сервер видит обрыв и прекращает генерацию (T-14).
    `transport` — подмена транспорта httpx (тесты).
    """

    def __init__(self, cfg: LLMConfig, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._cfg = cfg
        self._client = httpx.AsyncClient(
            base_url=cfg.base_url,
            timeout=httpx.Timeout(cfg.read_timeout_s, connect=cfg.connect_timeout_s),
            transport=transport,
            trust_env=False,  # системный прокси не должен перехватывать localhost
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._client.aclose()

    async def stream(
        self, messages: Sequence[Message], params: GenerationParams
    ) -> AsyncIterator[str]:
        """Дельты текста ответа; см. `LLMPort.stream`."""
        body = _chat_body(self._cfg.model, messages, params)
        try:
            async with self._client.stream("POST", CHAT_PATH, json=body) as response:
                await _check_status(response)
                async for line in response.aiter_lines():
                    payload = data_of(line)
                    if payload == SSE_DONE:
                        return
                    if payload and (text := delta_text(payload)):
                        yield text
        except _UNREACHABLE as exc:
            raise self._unavailable() from exc
        except httpx.HTTPError as exc:
            msg = f"Ответ LLM-сервера оборвался: {exc!r}"
            raise GenerationFailed(msg) from exc

    async def prefill(self, messages: Sequence[Message]) -> None:  # noqa: ARG002 — сигнатура порта
        """Общий OpenAI API не умеет прогрев кэша — только проверяет, что сервер отвечает."""
        try:
            response = await self._client.get(MODELS_PATH)
        except httpx.HTTPError as exc:
            raise self._unavailable() from exc
        if response.is_error:
            raise self._unavailable()

    def _unavailable(self) -> LLMUnavailable:
        return LLMUnavailable(
            f"LLM-сервер не отвечает на {self._cfg.base_url} — запущен ли scripts/start_llm.ps1?"
        )


def _chat_body(
    model: str, messages: Sequence[Message], params: GenerationParams
) -> dict[str, object]:
    body: dict[str, object] = {
        "model": model,
        "messages": [{"role": message.role.value, "content": message.text} for message in messages],
        "stream": True,
        "max_tokens": params.max_tokens,
        "temperature": params.temperature,
    }
    if params.stop:
        body["stop"] = list(params.stop)
    return body


async def _check_status(response: httpx.Response) -> None:
    if response.status_code == MODEL_LOADING_STATUS:
        msg = "LLM-сервер ещё загружает модель — повторите через несколько секунд"
        raise LLMUnavailable(msg)
    if response.is_error:
        text = (await response.aread()).decode(errors="replace")[:ERROR_BODY_LIMIT]
        msg = f"LLM-сервер ответил HTTP {response.status_code}: {text}"
        raise GenerationFailed(msg)
