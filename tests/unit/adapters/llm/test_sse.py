import pytest

from vtuber.adapters.llm.sse import SSE_DONE, data_of, delta_text
from vtuber.domain import GenerationFailed


@pytest.mark.parametrize(
    ("line", "payload"),
    [
        ('data: {"a": 1}', '{"a": 1}'),
        ('data:{"a": 1}', '{"a": 1}'),
        ("data: [DONE]", SSE_DONE),
        ("", None),
        (": keep-alive", None),
        ("event: message", None),
    ],
)
def test_only_data_lines_carry_payload(line: str, payload: str | None) -> None:
    assert data_of(line) == payload


def test_delta_text_takes_content_of_first_choice() -> None:
    assert delta_text('{"choices": [{"delta": {"content": "Привет"}}]}') == "Привет"


@pytest.mark.parametrize(
    "payload",
    [
        '{"choices": [{"delta": {"role": "assistant"}}]}',
        '{"choices": [{"delta": {"content": null}}]}',
        '{"choices": []}',
    ],
)
def test_chunks_without_text_give_empty_string(payload: str) -> None:
    assert delta_text(payload) == ""


@pytest.mark.parametrize("payload", ["{не json", '"строка"', '{"choices": "x"}', "{}"])
def test_malformed_chunk_is_generation_failure(payload: str) -> None:
    with pytest.raises(GenerationFailed):
        delta_text(payload)
