import pytest

from tests.fakes import FakeLLM
from vtuber.domain import GenerationFailed, LLMUnavailable, Message, Role
from vtuber.ports import GenerationParams

MESSAGES = (Message(Role.USER, "Привет"),)
PARAMS = GenerationParams(max_tokens=16, temperature=0.0)


async def _collect(llm: FakeLLM) -> list[str]:
    return [delta async for delta in llm.stream(MESSAGES, PARAMS)]


async def test_text_is_split_into_chunks_of_given_size() -> None:
    assert await _collect(FakeLLM("Привет!", chunk_size=3)) == ["При", "вет", "!"]


async def test_fails_after_given_number_of_chunks() -> None:
    stream = FakeLLM("abcdef", chunk_size=2, fail_after=2, error_type=GenerationFailed).stream(
        MESSAGES, PARAMS
    )

    assert [await anext(stream), await anext(stream)] == ["ab", "cd"]
    with pytest.raises(GenerationFailed):
        await anext(stream)


async def test_fail_after_zero_means_backend_is_unavailable() -> None:
    with pytest.raises(LLMUnavailable):
        await _collect(FakeLLM("abc", fail_after=0))


async def test_remembers_stream_and_prefill_requests() -> None:
    llm = FakeLLM("ok")

    await _collect(llm)
    await llm.prefill(MESSAGES)

    assert llm.calls == [(MESSAGES, PARAMS)]
    assert llm.prefills == [MESSAGES]
