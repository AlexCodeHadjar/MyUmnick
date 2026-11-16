"""Гейты навыков (ADR-0043): выключенный навык молчит, включённый — работает как раньше.

Обёртки читают реестр при каждом вызове: переключение действует со следующей реплики без
пересборки сервиса хода.
"""

from collections.abc import AsyncGenerator, Awaitable, Callable, Iterator, Mapping
from typing import Protocol

from vtuber.application.memory import TurnHints
from vtuber.domain import IncomingMessage
from vtuber.kernel import Command, MessageStream


class SkillGate(Protocol):
    """Что гейтам нужно от реестра навыков."""

    def enabled(self, skill_id: str) -> bool:
        """Включён ли навык."""
        ...

    def record(self, skill_id: str, ms: float | None) -> None:
        """Навык сработал за `ms` или (`None`) не успел."""
        ...


class EnabledCommands(Mapping[str, Command]):
    """Команды ведущего без выключенных: выключенная команда идёт к модели обычной репликой."""

    def __init__(
        self, commands: Mapping[str, Command], skills: Mapping[str, str], gate: SkillGate
    ) -> None:
        self._commands = commands
        self._skills = skills
        self._gate = gate

    def __getitem__(self, text: str) -> Command:
        if not self._gate.enabled(self._skills.get(text, "")):
            raise KeyError(text)
        return self._commands[text]

    def __iter__(self) -> Iterator[str]:
        return (text for text in self._commands if self._gate.enabled(self._skills.get(text, "")))

    def __len__(self) -> int:
        return sum(1 for _ in self)


def gated_stream(stream: MessageStream, skill_id: str, gate: SkillGate) -> MessageStream:
    """Реплики источника, пока навык включён; выключенный — реплики читаются и отбрасываются.

    Источник продолжает читаться, чтобы после включения не выдать пачку устаревших сообщений.
    """

    async def gated() -> AsyncGenerator[IncomingMessage]:
        async for message in stream():
            if gate.enabled(skill_id):
                yield message

    return gated


type Hints = Callable[[str], Awaitable[TurnHints]]
"""Справка хода по реплике (как `HintSource` сервиса хода)."""


def gated_hints(hints: Hints, skill_id: str, gate: SkillGate) -> Hints:
    """Встроенный навык справки (память): выключен — ход идёт без неё и без затрат на неё."""

    async def gated(text: str) -> TurnHints:
        return await hints(text) if gate.enabled(skill_id) else TurnHints()

    return gated
