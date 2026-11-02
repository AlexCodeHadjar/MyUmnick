"""Адаптер LLMPort для llama-server: слот диалога, переиспользование KV-кэша, prefill."""

from collections.abc import Sequence
from typing import Final, override

import httpx

from vtuber.adapters.llm.openai_compat import (
    UNREACHABLE,
    OpenAICompatLLM,
    check_status,
    wire_messages,
)
from vtuber.domain import GenerationFailed, Message
from vtuber.ports import GenerationParams

# Иврит и арабица … сингальский, тайский, кана, ханьцзы, хангыль: модель изредка вставляет такие
# символы в русский текст (宿敵), а голос их не прочтёт. Запрет на уровне генерации надёжнее правила
# в промпте и не снижает скорость (docs/perf/gpu-run-2026-11-02.md). Латиница разрешена.
FOREIGN_SCRIPTS: Final = (
    (0x0590, 0x0DFF),
    (0x0E00, 0x0E7F),
    (0x3040, 0x30FF),
    (0x3400, 0x9FFF),
    (0xAC00, 0xD7AF),
    (0xF900, 0xFAFF),
)
NO_FOREIGN_SCRIPTS_GRAMMAR: Final = (
    "root ::= [^" + "".join(f"{chr(low)}-{chr(high)}" for low, high in FOREIGN_SCRIPTS) + "]*"
)
APPLY_TEMPLATE_PATH: Final = "/apply-template"
COMPLETION_PATH: Final = "/completion"


class LlamaCppLLM(OpenAICompatLLM):
    """OpenAI-совместимый стрим + особенности llama-server.

    Каждый запрос закреплён за слотом диалога и переиспользует его KV-кэш (`cache_prompt`, T-03);
    reasoning-режим шаблона выключается в запросе (T-08), а глобально — флагом сервера
    `--reasoning-budget 0` в `scripts/start_llm.ps1`.
    """

    @override
    async def prefill(self, messages: Sequence[Message]) -> None:
        """Прогревает KV-кэш слота диалога без генерации (T-05, T-06).

        Промпт строится шаблоном самой модели (`/apply-template`), поэтому совпадает с тем, что
        отрендерит чат, и кэш переиспользуется; затем `/completion` с `n_predict: 0`.
        """
        options = self._cfg.llamacpp
        template_body = {"messages": wire_messages(messages), **self._template_kwargs()}
        try:
            template = await self._client.post(APPLY_TEMPLATE_PATH, json=template_body)
            await check_status(template)
            completion_body = {
                "prompt": _prompt_of(template),
                "n_predict": 0,
                "cache_prompt": True,
                "id_slot": options.slot_id,
            }
            await check_status(await self._client.post(COMPLETION_PATH, json=completion_body))
        except UNREACHABLE as exc:
            raise self._unavailable() from exc
        except httpx.HTTPError as exc:
            msg = f"Прогрев кэша llama-server не удался: {exc!r}"
            raise GenerationFailed(msg) from exc

    @override
    def _request_body(
        self, messages: Sequence[Message], params: GenerationParams
    ) -> dict[str, object]:
        return {
            **super()._request_body(messages, params),
            "id_slot": self._cfg.llamacpp.slot_id,
            "cache_prompt": True,
            **self._template_kwargs(),
            **self._grammar(),
        }

    def _grammar(self) -> dict[str, object]:
        if not self._cfg.llamacpp.forbid_foreign_scripts:
            return {}
        return {"grammar": NO_FOREIGN_SCRIPTS_GRAMMAR}

    def _template_kwargs(self) -> dict[str, object]:
        return {"chat_template_kwargs": {"enable_thinking": self._cfg.llamacpp.enable_thinking}}


def _prompt_of(response: httpx.Response) -> str:
    try:
        prompt = response.json()["prompt"]  # boundary: нетипизированный JSON сервера (R-18)
    except (ValueError, KeyError, TypeError) as exc:
        msg = f"llama-server вернул неожиданный ответ /apply-template: {response.text[:200]!r}"
        raise GenerationFailed(msg) from exc
    if not isinstance(prompt, str):
        msg = f"llama-server вернул промпт не строкой: {prompt!r}"
        raise GenerationFailed(msg)
    return prompt
