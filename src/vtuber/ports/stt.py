"""Порты голосового ввода: детектор речи и распознавание — раздельно (ISP).

Детектор слушает каждый кадр в реальном времени, распознавание зовут редко и на готовый отрезок:
у них разные модели, частота вызовов и цена ошибки.
"""

from typing import Protocol

from vtuber.domain import AudioChunk, AudioFormat, SoundKind


class SoundClassifierPort(Protocol):
    """Какой звук в окне, кроме речи (S-14.4)."""

    async def classify(self, audio: AudioChunk) -> SoundKind | None:
        """Звук окна; речь, тишина и неизвестное — None.

        Raises:
            STTUnavailable: модель не загружена.
            GenerationFailed: разбор сорвался.

        """
        ...


class SpeakerEmbedderPort(Protocol):
    """Отпечаток голоса фразы (S-14.3): у одного человека отпечатки близки."""

    async def embed(self, audio: AudioChunk) -> tuple[float, ...]:
        """Вектор фиксированной длины.

        Raises:
            STTUnavailable: модель не загружена.
            GenerationFailed: фраза не подошла или разбор сорвался.

        """
        ...


class VadPort(Protocol):
    """Детектор речи: окно PCM → вероятность, что это речь.

    Контракт — `tests/contract/test_stt_contract.py`: тишина — низкая вероятность, речь — высокая,
    окно другой длины — `ValueError`, недоступная модель — `STTUnavailable`.
    """

    @property
    def audio_format(self) -> AudioFormat:
        """Частота, на которую рассчитана модель."""
        ...

    @property
    def window_samples(self) -> int:
        """Длина окна в сэмплах: модель принимает только её."""
        ...

    async def speech_probability(self, pcm: bytes) -> float:
        """Вероятность речи 0…1 в окне PCM s16le; модель помнит предыдущие окна.

        Raises:
            ValueError: длина окна не `window_samples`.
            STTUnavailable: модель не загружена.

        """
        ...

    def reset(self) -> None:
        """Забыть прошлые окна: новая фраза не зависит от предыдущей."""
        ...


class STTPort(Protocol):
    """Распознавание отрезка речи.

    Промежуточные гипотезы — тот же вызов на накопленном звуке: Whisper не потоковый, а частоту
    вызовов лучше решать снаружи, вместе с бюджетом CPU или GPU.
    """

    async def transcribe(self, audio: AudioChunk, *, final: bool) -> str:
        """Текст отрезка; тишина — пустая строка. `final=False` — быстрее, но менее точно.

        Raises:
            STTUnavailable: модель не загружена.
            GenerationFailed: распознавание сорвалось.

        """
        ...
