"""Сервер голоса и выбор запасного движка (ADR-0031); общий контракт — в tests/contract."""

from typing import Self

import httpx
import pytest

from tests.fakes import FakeTTS
from vtuber.adapters.tts import FallbackTTS, VoiceServerConfig, VoiceServerTTS
from vtuber.domain import GenerationFailed, TTSUnavailable

SAMPLE_RATE = 24000


def _cfg() -> VoiceServerConfig:
    return VoiceServerConfig(
        base_url="http://voice.test",
        connect_timeout_s=0.2,
        read_timeout_s=1,
        sample_rate=SAMPLE_RATE,
        chunk_ms=100,
    )


def _server(
    health_rate: int = SAMPLE_RATE, synth_status: int = 200, pcm: bytes = b""
) -> VoiceServerTTS:
    def reply(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"sample_rate": health_rate})
        return httpx.Response(synth_status, content=pcm)

    return VoiceServerTTS(_cfg(), transport=httpx.MockTransport(reply), check_pause_s=0)


def _down() -> VoiceServerTTS:
    def reply(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    return VoiceServerTTS(_cfg(), transport=httpx.MockTransport(reply), check_pause_s=0)


class _Spare(FakeTTS):
    """Запасной движок, который помнит, загружали ли его."""

    entered = False

    async def __aenter__(self) -> Self:
        self.entered = True
        return self

    async def __aexit__(self, *_: object) -> None:
        self.entered = False


async def test_pcm_is_cut_into_chunks_of_whole_samples() -> None:
    async with _server(pcm=b"\x01\x00" * 3000 + b"\x01") as tts:
        chunks = [chunk async for chunk in tts.synthesize("Привет")]

    assert [len(chunk.pcm) for chunk in chunks] == [4800, 1200]


async def test_phrase_without_letters_does_not_reach_the_server() -> None:
    async with _down() as tts:
        assert [chunk async for chunk in tts.synthesize("…")] == []


async def test_server_error_is_generation_failed() -> None:
    async with _server(synth_status=500) as tts:
        with pytest.raises(GenerationFailed, match="500"):
            _ = [chunk async for chunk in tts.synthesize("Привет")]


async def test_other_sample_rate_is_a_problem_with_a_hint() -> None:
    async with _server(health_rate=48000) as tts:
        assert tts.problem is not None
        assert "sample_rate" in tts.problem


async def test_dropped_tunnel_is_unavailable_and_recovers_by_itself() -> None:
    reachable = False

    def reply(request: httpx.Request) -> httpx.Response:
        if not reachable:
            raise httpx.ConnectError("no route", request=request)
        return httpx.Response(200, json={"sample_rate": SAMPLE_RATE}, content=None)

    async with VoiceServerTTS(_cfg(), transport=httpx.MockTransport(reply), check_pause_s=0) as tts:
        with pytest.raises(TTSUnavailable):
            _ = [chunk async for chunk in tts.synthesize("Привет")]
        reachable = True
        assert [chunk async for chunk in tts.synthesize("Привет")]


async def test_brief_outage_at_start_is_retried() -> None:
    calls = 0

    def reply(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectError("no route", request=request)
        return httpx.Response(200, json={"sample_rate": SAMPLE_RATE})

    async with VoiceServerTTS(_cfg(), transport=httpx.MockTransport(reply), check_pause_s=0) as tts:
        assert tts.problem is None


async def test_ready_server_speaks_and_spare_engine_is_not_loaded() -> None:
    spare = _Spare()
    async with FallbackTTS(_server(pcm=b"\x01\x00" * 100), spare) as tts:
        assert tts.audio_format.sample_rate == SAMPLE_RATE
        assert [chunk async for chunk in tts.synthesize("Привет")]
        assert not spare.entered


async def test_unreachable_server_hands_over_to_spare_engine() -> None:
    spare = _Spare()
    async with FallbackTTS(_down(), spare) as tts:
        assert spare.entered
        assert tts.audio_format == spare.audio_format
        assert [chunk async for chunk in tts.synthesize("Привет")]
    assert not spare.entered
