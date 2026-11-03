"""Режим «по имени» (S-14.1, ADR-0026): посторонний разговор в комнате не запускает ход.

Имя ищется в тексте Whisper: новой модели не нужно, русский уже работает, а своё имя задаётся в
конфиге. Звук без обращения никуда не идёт: фраза отбрасывается, текст её не сохраняется.
"""

import re
from typing import Literal

from pydantic import Field

from vtuber.application.voice.listener import VoiceEvents
from vtuber.kernel import ConfigSection, get_logger

_log = get_logger(__name__)
_CALL_WORDS = r"(?:(?:эй|хей|слушай|привет|ну|окей|так)[\s,!.:-]+)*"
_NOT_IN_WORD = r"(?![а-яёa-z0-9])"


class AddressingConfig(ConfigSection):
    """Подсекция `[stt.addressing]`: `always` — любая речь, `by_name` — только обращение."""

    mode: Literal["always", "by_name"]
    names: tuple[str, ...] = Field(min_length=1)


def name_pattern(names: tuple[str, ...]) -> re.Pattern[str]:
    """Обращение: имя в начале, можно после «эй», или в самом конце («как дела, Мика?»)."""
    any_name = "|".join(re.escape(name) for name in names)
    start = rf"^[\s\"«]*{_CALL_WORDS}(?:{any_name}){_NOT_IN_WORD}"
    end = rf"[\s,](?:{any_name})[\s.!?…\"»]*$"
    return re.compile(f"{start}|{end}", re.IGNORECASE)


class AddressedEvents:
    """Пропускает голосовые события, только если обратились по имени.

    Перебить голосом тоже можно только по имени: иначе чужая речь обрывала бы витюбера. Имя видно
    лишь в промежуточной гипотезе, поэтому перебивание здесь позже, чем в режиме `always`.
    """

    def __init__(self, inner: VoiceEvents, names: tuple[str, ...]) -> None:
        self._inner = inner
        self._pattern = name_pattern(names)
        self._barged = False

    async def barge_in(self) -> None:
        """Речь без текста: кто и к кому обращается, пока неизвестно."""

    async def hypothesis(self, text: str) -> None:
        """Чужая речь не показывается и не греет кэш."""
        if self._pattern.search(text):
            await self._barge_once()
            await self._inner.hypothesis(text)

    async def final(self, text: str, ended_ns: int) -> None:
        """Фраза с обращением становится репликой; остальные отбрасываются."""
        if self._pattern.search(text):
            await self._barge_once()
            await self._inner.final(text, ended_ns)
        else:
            _log.info("voice.not_addressed")
        self._barged = False

    async def _barge_once(self) -> None:
        if not self._barged:
            self._barged = True
            await self._inner.barge_in()


def addressed(cfg: AddressingConfig, events: VoiceEvents) -> VoiceEvents:
    """В режиме `always` обёртки нет: лишний шаг в горячем пути ни к чему."""
    return events if cfg.mode == "always" else AddressedEvents(events, cfg.names)
