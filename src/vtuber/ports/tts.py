"""Порт синтеза речи: фраза → поток PCM в формате, который движок объявляет заранее."""

from collections.abc import AsyncGenerator
from typing import Protocol

from vtuber.domain import AudioChunk, AudioFormat


class TTSPort(Protocol):
    """Движок TTS; адаптеры бросают только доменные ошибки (R-43).

    Контракт для каждого адаптера — `tests/contract/test_tts_contract.py` (R-57, принцип L):
    формат, отмена, ошибки одинаковы у всех движков — конвейер не знает, какой из них работает.
    """

    @property
    def audio_format(self) -> AudioFormat:
        """Формат всех фрагментов этого движка: частота разная у движков, ресемплинг — в UI."""
        ...

    def synthesize(self, phrase: str) -> AsyncGenerator[AudioChunk]:
        """Синтезирует фразу; движки со стримингом отдают несколько фрагментов (T-02).

        Каждый фрагмент — в `audio_format`, целое число сэмплов. Пустая фраза (одни пробелы) —
        ни одного фрагмента, не ошибка. Отмена задачи-потребителя прекращает синтез, а
        `CancelledError` не подавляется (T-14, R-38). Генератор, а не просто итератор:
        потребитель закрывает его через `contextlib.aclosing` при любом выходе (R-37).

        Raises:
            TTSUnavailable: модель не загружена или движок не отвечает.
            GenerationFailed: синтез сорвался посреди фразы.

        """
        ...
