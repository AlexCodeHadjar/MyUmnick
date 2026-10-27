import pytest

from vtuber.domain import (
    BackendUnavailable,
    GenerationFailed,
    LLMUnavailable,
    ProtocolError,
    TTSUnavailable,
    VtuberError,
)


@pytest.mark.parametrize("error", [LLMUnavailable, TTSUnavailable])
def test_backend_errors_are_caught_as_backend_unavailable(error: type[VtuberError]) -> None:
    assert issubclass(error, BackendUnavailable)


@pytest.mark.parametrize("error", [BackendUnavailable, GenerationFailed, ProtocolError])
def test_every_domain_error_is_a_vtuber_error(error: type[Exception]) -> None:
    assert issubclass(error, VtuberError)


def test_error_keeps_actionable_message() -> None:
    message = "LLM-сервер не отвечает на 127.0.0.1:8080 — запущен ли scripts/start_llm?"

    assert str(LLMUnavailable(message)) == message
