"""TTS-ветка хода: фразы из очереди → нормализация → синтез → `sink.audio` (T-02).

Работает параллельно с генерацией: пока LLM пишет фразу N+1, фраза N уже звучит. Ошибка движка
не обрывает ход — текст ответа важнее голоса: недоступный TTS молчит до конца хода, сбой одной
фразы пропускает только её. Звук ответа не готов к сроку — междометие из `FillerBank` (T-17).
"""

import asyncio
from contextlib import ExitStack, aclosing

from vtuber.application.pipeline.filler import AudioOut, FillerBank
from vtuber.application.speech import normalize_for_speech
from vtuber.domain import GenerationFailed, TTSUnavailable
from vtuber.kernel import Telemetry, get_logger
from vtuber.ports import ReplySink, TTSPort

type PhraseQueue = asyncio.Queue[str | None]
"""Фразы хода; None — конец ответа."""

_log = get_logger(__name__)


class Speaker:
    """Озвучивает фразы одного хода.

    Замеры: `tts.first_audio` — от начала хода до первого звука ответа (TTFA ядра, без сети и
    плеера UI; междометие не в счёт), `tts.phrase` — синтез и отдача одной фразы.
    """

    def __init__(
        self, tts: TTSPort, telemetry: Telemetry, fillers: FillerBank | None = None
    ) -> None:
        self._tts = tts
        self._telemetry = telemetry
        self._fillers = fillers

    async def run(self, phrases: PhraseQueue, sink: ReplySink) -> None:
        """Озвучивает фразы до None; отмена (новый ход, «Стоп») прерывает синтез сразу (T-14)."""
        out = AudioOut(sink)
        filler = self._start_filler(out)
        try:
            with ExitStack() as first_audio:
                first_audio.enter_context(self._telemetry.span("tts.first_audio"))
                try:
                    await self._speak_all(phrases, out, first_audio)
                except TTSUnavailable as error:
                    _log.warning("tts.unavailable", problem=str(error))
                # Звука в ходе не было — «время до первого звука» не измерено, а не равно ходу.
                first_audio.pop_all()
        finally:
            if filler is not None:
                filler.cancel()
                await asyncio.wait([filler])

    def _start_filler(self, out: AudioOut) -> asyncio.Task[None] | None:
        bank = self._fillers
        if bank is None or not bank.ready:
            return None
        return asyncio.create_task(_say_filler(bank, out))

    async def _speak_all(self, phrases: PhraseQueue, out: AudioOut, first: ExitStack) -> None:
        while (phrase := await phrases.get()) is not None:
            text = normalize_for_speech(phrase)
            if not text:
                continue
            try:
                await self._speak(text, out, first)
            except GenerationFailed as error:
                _log.warning("tts.phrase_failed", problem=str(error))

    async def _speak(self, text: str, out: AudioOut, first: ExitStack) -> None:
        with self._telemetry.span("tts.phrase"):
            async with aclosing(self._tts.synthesize(text)) as audio:
                async for chunk in audio:
                    await out.answer(chunk)
                    # Первый звук хода: закрыть замер TTFA; повторное закрытие — пустое.
                    first.close()


async def _say_filler(bank: FillerBank, out: AudioOut) -> None:
    """К сроку звука ответа нет — междометие (ответ, начавшись раньше, его отменяет)."""
    await asyncio.sleep(bank.after_s)
    if await out.filler(bank.next_clip()):
        _log.info("tts.filler")
