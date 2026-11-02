"""Фейки для тестов без GPU, сети и реального времени (R-56)."""

from tests.fakes.clock import FakeClock
from tests.fakes.fake_embedder import FakeEmbedder
from tests.fakes.fake_llm import FakeLLM
from tests.fakes.fake_memory_store import FakeMemoryStore
from tests.fakes.fake_stt import FakeSTT, FakeVad
from tests.fakes.fake_tts import FakeTTS
from tests.fakes.recording_sink import RecordingSink

__all__ = [
    "FakeClock",
    "FakeEmbedder",
    "FakeLLM",
    "FakeMemoryStore",
    "FakeSTT",
    "FakeTTS",
    "FakeVad",
    "RecordingSink",
]
