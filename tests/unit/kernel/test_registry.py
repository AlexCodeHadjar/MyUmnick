from dataclasses import dataclass

import pytest

from vtuber.domain import ConfigError
from vtuber.kernel import Registry


@dataclass(frozen=True)
class _Voice:
    rate: int


def _registry() -> Registry[int, _Voice]:
    return Registry[int, _Voice]("tts")


def test_created_object_comes_from_registered_factory() -> None:
    voices = _registry()
    voices.add("double", lambda rate: _Voice(rate * 2))

    assert voices.create("double", 12000) == _Voice(24000)


def test_classes_can_be_registered_directly() -> None:
    voices = _registry()
    voices.add("plain", _Voice)

    assert voices.create("plain", 8000) == _Voice(8000)


def test_duplicate_name_is_rejected() -> None:
    voices = _registry()
    voices.add("silero", _Voice)

    with pytest.raises(ValueError, match="silero"):
        voices.add("silero", _Voice)


def test_unknown_name_is_config_error_listing_known_names() -> None:
    voices = _registry()
    voices.add("silero", _Voice)
    voices.add("piper", _Voice)

    with pytest.raises(ConfigError, match=r"tts 'xtts'.*piper, silero"):
        voices.create("xtts", 1)
