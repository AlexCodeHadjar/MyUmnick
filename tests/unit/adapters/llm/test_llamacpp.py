import json
from collections.abc import Callable

import httpx
import pytest

from vtuber.adapters.llm import GenerationConfig, LlamaCppLLM, LlamaCppOptions, LLMConfig
from vtuber.adapters.llm.llamacpp import NO_FOREIGN_SCRIPTS_GRAMMAR
from vtuber.domain import GenerationFailed, LLMUnavailable, Message, Role
from vtuber.ports import GenerationParams

CFG = LLMConfig(
    base_url="http://llama.test",
    model="local",
    connect_timeout_s=1,
    read_timeout_s=5,
    llamacpp=LlamaCppOptions(
        slot_id=0, enable_thinking=False, forbid_foreign_scripts=True, forbid_cyrillic=False
    ),
    backend="llamacpp",
    generation=GenerationConfig(max_tokens=64, temperature=0.5),
)
MESSAGES = (Message(Role.SYSTEM, "Ты Мика."), Message(Role.USER, "Привет!"))
WIRE_MESSAGES = [
    {"role": "system", "content": "Ты Мика."},
    {"role": "user", "content": "Привет!"},
]
PARAMS = GenerationParams(max_tokens=32, temperature=0.5)
PROMPT = "<|im_start|>system\nТы Мика.<|im_end|>\n"

type Handler = Callable[[httpx.Request], httpx.Response]


def _recording(answers: dict[str, httpx.Response]) -> tuple[Handler, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return answers[request.url.path]

    return handler, seen


async def test_chat_request_pins_dialog_slot_reuses_cache_and_disables_thinking() -> None:
    handler, seen = _recording(
        {"/v1/chat/completions": httpx.Response(200, text="data: [DONE]\n\n")}
    )

    async with LlamaCppLLM(CFG, transport=httpx.MockTransport(handler)) as llm:
        assert [delta async for delta in llm.stream(MESSAGES, PARAMS)] == []

    body = json.loads(seen[0].content)
    assert body["messages"] == WIRE_MESSAGES
    assert body["stream"] is True
    assert body["id_slot"] == 0
    assert body["cache_prompt"] is True
    assert body["chat_template_kwargs"] == {"enable_thinking": False}


async def test_chat_request_forbids_foreign_scripts_only_when_configured() -> None:
    allowed = CFG.model_copy(
        update={"llamacpp": CFG.llamacpp.model_copy(update={"forbid_foreign_scripts": False})}
    )

    body = LlamaCppLLM(CFG)._request_body(MESSAGES, PARAMS)  # noqa: SLF001
    assert body["grammar"] == NO_FOREIGN_SCRIPTS_GRAMMAR
    assert "grammar" not in LlamaCppLLM(allowed)._request_body(MESSAGES, PARAMS)  # noqa: SLF001
    assert chr(0x3400) in NO_FOREIGN_SCRIPTS_GRAMMAR


async def test_english_edition_also_forbids_cyrillic() -> None:
    english = CFG.model_copy(
        update={"llamacpp": CFG.llamacpp.model_copy(update={"forbid_cyrillic": True})}
    )

    grammar = LlamaCppLLM(english)._request_body(MESSAGES, PARAMS)["grammar"]  # noqa: SLF001

    assert isinstance(grammar, str)
    assert "Ѐ-ԯ" in grammar
    assert "Ѐ" not in NO_FOREIGN_SCRIPTS_GRAMMAR


async def test_prefill_renders_template_then_evaluates_prompt_without_generation() -> None:
    handler, seen = _recording(
        {
            "/apply-template": httpx.Response(200, json={"prompt": PROMPT}),
            "/completion": httpx.Response(200, json={"content": ""}),
        }
    )

    async with LlamaCppLLM(CFG, transport=httpx.MockTransport(handler)) as llm:
        await llm.prefill(MESSAGES)

    template, completion = seen
    assert template.url.path == "/apply-template"
    assert json.loads(template.content) == {
        "messages": WIRE_MESSAGES,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    assert completion.url.path == "/completion"
    assert json.loads(completion.content) == {
        "prompt": PROMPT,
        "n_predict": 0,
        "cache_prompt": True,
        "id_slot": 0,
    }


async def test_prefill_while_model_loads_is_unavailable() -> None:
    handler, _ = _recording({"/apply-template": httpx.Response(503, text="Loading model")})

    async with LlamaCppLLM(CFG, transport=httpx.MockTransport(handler)) as llm:
        with pytest.raises(LLMUnavailable, match="загружает"):
            await llm.prefill(MESSAGES)


async def test_prefill_without_server_is_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    async with LlamaCppLLM(CFG, transport=httpx.MockTransport(handler)) as llm:
        with pytest.raises(LLMUnavailable, match="start_llm"):
            await llm.prefill(MESSAGES)


@pytest.mark.parametrize("answer", [{"prompt": 42}, {}, ["prompt"]])
async def test_prefill_with_unexpected_template_answer_fails(answer: object) -> None:
    handler, _ = _recording({"/apply-template": httpx.Response(200, json=answer)})

    async with LlamaCppLLM(CFG, transport=httpx.MockTransport(handler)) as llm:
        with pytest.raises(GenerationFailed):
            await llm.prefill(MESSAGES)


async def test_prefill_error_from_completion_is_generation_failure() -> None:
    handler, _ = _recording(
        {
            "/apply-template": httpx.Response(200, json={"prompt": PROMPT}),
            "/completion": httpx.Response(400, text="context overflow"),
        }
    )

    async with LlamaCppLLM(CFG, transport=httpx.MockTransport(handler)) as llm:
        with pytest.raises(GenerationFailed, match="context overflow"):
            await llm.prefill(MESSAGES)


async def test_prefill_read_timeout_is_generation_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/completion":
            raise httpx.ReadTimeout("slow prefill", request=request)
        return httpx.Response(200, json={"prompt": PROMPT})

    async with LlamaCppLLM(CFG, transport=httpx.MockTransport(handler)) as llm:
        with pytest.raises(GenerationFailed, match="Прогрев"):
            await llm.prefill(MESSAGES)
