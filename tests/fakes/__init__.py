"""Фейки для тестов без GPU, сети и реального времени (R-56)."""

from tests.fakes.clock import FakeClock
from tests.fakes.fake_llm import FakeLLM

__all__ = ["FakeClock", "FakeLLM"]
