"""Порты голосового ввода: детектор речи и распознавание — раздельно (ISP).

Детектор слушает каждый кадр в реальном времени, распознавание зовут редко и на готовый отрезок:
у них разные модели, частота вызовов и цена ошибки.
"""

from typing import Protocol

from vtuber.domain import AudioChunk, AudioFormat


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
