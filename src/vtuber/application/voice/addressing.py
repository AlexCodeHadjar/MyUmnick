"""Режим «по имени» (S-14.1, ADR-0026): посторонний разговор в комнате не запускает ход.

Имя ищется в тексте Whisper: новой модели не нужно, русский уже работает, а своё имя задаётся в
конфиге. Звук без обращения никуда не идёт: фраза отбрасывается, текст её не сохраняется.
"""

import re
import time
from collections.abc import Callable
from typing import Literal

from pydantic import Field

from vtuber.application.voice.listener import VoiceEvents
from vtuber.application.voice.speakers import SPEAKER_WORD
from vtuber.kernel import ConfigSection, get_logger

_log = get_logger(__name__)
_CALL_WORDS = (
    r"(?:(?:эй|хей|слушай|привет|ну|окей|так|hey|hi|hello|ok|okay|so|listen|yo)"
    r"[\s,!.:-]+)*"
)
_SPEAKER_LABEL = rf"(?:{SPEAKER_WORD} \d+: )?"
_NOT_IN_WORD = r"(?![а-яёa-z0-9])"


class AddressingConfig(ConfigSection):
    """Подсекция `[stt.addressing]`: `always` — любая речь, `by_name` — только обращение.

    `follow_up_s` — сколько ждать запроса после одного имени («Умник» … «какая погода?»).
    """

    mode: Literal["always", "by_name"]
    names: tuple[str, ...] = Field(min_length=1)
    follow_up_s: float = Field(gt=0)


def name_pattern(names: tuple[str, ...]) -> re.Pattern[str]:
    """Обращение: имя в начале, можно после «эй», или в самом конце («как дела, Мика?»)."""
    any_name = "|".join(re.escape(name) for name in names)
    start = rf"^{_SPEAKER_LABEL}[\s\"«]*{_CALL_WORDS}(?:{any_name}){_NOT_IN_WORD}"
    end = rf"[\s,](?:{any_name})[\s.!?…\"»]*$"
    return re.compile(f"{start}|{end}", re.IGNORECASE)


def without_call(text: str, pattern: re.Pattern[str]) -> str:
    """Запрос без обращения: «Эй, Умник, какая погода?» → «какая погода?»; метка остаётся."""
    label = re.match(rf"^{_SPEAKER_LABEL}", text)
    prefix = label.group() if label else ""
    request = pattern.sub(" ", text, count=1)
    request = request.removeprefix(prefix) if prefix and request.startswith(prefix) else request
    request = request.strip(' ,.!?…:;-—"«»')
    return f"{prefix}{request}" if request else ""


class AddressedEvents:
    """Пропускает голосовые события, только если обратились по имени; имя из запроса вырезается.

    Одно имя без запроса («Умник!») открывает окно `follow_up_s`: следующая фраза — запрос, даже без
    имени. Перебить голосом тоже можно только по имени: иначе чужая речь обрывала бы витюбера. Имя
    видно лишь в промежуточной гипотезе, поэтому перебивание здесь позже, чем в режиме `always`.
    """

    def __init__(
        self,
        inner: VoiceEvents,
        names: tuple[str, ...],
        follow_up_s: float = 8.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._inner = inner
        self._pattern = name_pattern(names)
        self._follow_up_s = follow_up_s
        self._clock = clock
        self._barged = False
        self._armed_until = 0.0

    async def barge_in(self) -> None:
        """Речь без текста: кто и к кому обращается, пока неизвестно."""

    async def hypothesis(self, text: str) -> None:
        """Чужая речь не показывается и не греет кэш."""
        if self._pattern.search(text) or self._armed():
            await self._barge_once()
            await self._inner.hypothesis(without_call(text, self._pattern) or text)

    async def final(self, text: str, ended_ns: int) -> None:
        """Фраза с обращением — запрос без имени; одно имя ждёт запрос следующей фразой."""
        called = bool(self._pattern.search(text))
        if called or self._armed():
            await self._barge_once()
            request = without_call(text, self._pattern) if called else text
            if request:
                self._armed_until = 0.0
                await self._inner.final(request, ended_ns)
            else:
                self._armed_until = self._clock() + self._follow_up_s
                _log.info("voice.called_waiting")
        else:
            _log.info("voice.not_addressed")
        self._barged = False

    def _armed(self) -> bool:
        return self._clock() < self._armed_until

    async def _barge_once(self) -> None:
        if not self._barged:
            self._barged = True
            await self._inner.barge_in()


def addressed(cfg: AddressingConfig, events: VoiceEvents) -> VoiceEvents:
    """В режиме `always` обёртки нет: лишний шаг в горячем пути ни к чему."""
    if cfg.mode == "always":
        return events
    return AddressedEvents(events, cfg.names, cfg.follow_up_s)
