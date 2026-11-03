"""Адаптер LLMPort для OpenAI-совместимого API (`/v1/chat/completions`, стрим SSE)."""

from collections.abc import AsyncGenerator, Sequence
from types import TracebackType
from typing import Final, Self

import httpx

from vtuber.adapters.llm.config import LLMConfig
from vtuber.adapters.llm.sse import SSE_DONE, data_of, delta_text
from vtuber.domain import GenerationFailed, LLMUnavailable, Message, VisionUnavailable
from vtuber.ports import GenerationParams

CHAT_PATH: Final = "/v1/chat/completions"
MODELS_PATH: Final = "/v1/models"
MODEL_LOADING_STATUS: Final = 503
ERROR_BODY_LIMIT: Final = 300
NO_VISION_MESSAGE: Final = (
    "Модель не смогла посмотреть картинку. Для этого llama-server запускают с проектором: "
    "--mmproj, настройка [llama_server].mmproj."
)
UNREACHABLE: Final = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)


class OpenAICompatLLM:
    """Стрим ответа по HTTP/SSE; один httpx-клиент на всё время жизни (R-40, ADR-0007).

    Использовать как `async with OpenAICompatLLM(cfg) as llm` — выход закрывает соединения.
    Отмена потребителя закрывает ответ, сервер видит обрыв и прекращает генерацию (T-14).
    `transport` — подмена транспорта httpx (тесты). Наследники дополняют тело запроса
    через `_request_body`.
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
    ) -> AsyncGenerator[str]:
        """Дельты текста ответа; см. `LLMPort.stream`."""
        body = self._request_body(messages, params)
        try:
            async with self._client.stream("POST", CHAT_PATH, json=body) as response:
                await _check_with_images(response, messages)
                async for line in response.aiter_lines():
                    payload = data_of(line)
                    if payload == SSE_DONE:
                        return
                    if payload and (text := delta_text(payload)):
                        yield text
        except UNREACHABLE as exc:
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

    def _request_body(
        self, messages: Sequence[Message], params: GenerationParams
    ) -> dict[str, object]:
        body: dict[str, object] = {
            "model": self._cfg.model,
            "messages": wire_messages(messages),
            "stream": True,
            "max_tokens": params.max_tokens,
            "temperature": params.temperature,
        }
        if params.stop:
            body["stop"] = list(params.stop)
        return body

    def _unavailable(self) -> LLMUnavailable:
        return LLMUnavailable(
            f"LLM-сервер не отвечает на {self._cfg.base_url} — запущен ли scripts/start_llm.ps1?"
        )


def wire_messages(messages: Sequence[Message]) -> list[dict[str, object]]:
    """Сообщения в формате OpenAI Chat API; без картинки — обычной строкой, как всегда."""
    return [{"role": message.role.value, "content": _content(message)} for message in messages]


def _content(message: Message) -> str | list[dict[str, object]]:
    if not message.images:
        return message.text
    images: list[dict[str, object]] = [
        {"type": "image_url", "image_url": {"url": f"data:{image.mime};base64,{image.base64}"}}
        for image in message.images
    ]
    return [{"type": "text", "text": message.text}, *images]


async def _check_with_images(response: httpx.Response, messages: Sequence[Message]) -> None:
    """Сервер без проектора на картинку отвечает общей ошибкой: заранее его не спрашиваем."""
    try:
        await check_status(response)
    except GenerationFailed as exc:
        if any(message.images for message in messages):
            raise VisionUnavailable(NO_VISION_MESSAGE) from exc
        raise


async def check_status(response: httpx.Response) -> None:
    """Переводит HTTP-код ошибки в доменную: 503 (модель грузится) — недоступность, иное — сбой.

    Raises:
        LLMUnavailable: HTTP 503.
        GenerationFailed: другой код ошибки; текст ответа сервера — в сообщении.

    """
    if response.status_code == MODEL_LOADING_STATUS:
        msg = "LLM-сервер ещё загружает модель — повторите через несколько секунд"
        raise LLMUnavailable(msg)
    if response.is_error:
        text = (await response.aread()).decode(errors="replace")[:ERROR_BODY_LIMIT]
        msg = f"LLM-сервер ответил HTTP {response.status_code}: {text}"
        raise GenerationFailed(msg)
