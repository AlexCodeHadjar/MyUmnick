"""Дерево диалога (S-16.1): вернуться к реплике и продолжить иначе; прежняя ветка остаётся."""

from collections.abc import Iterable
from dataclasses import dataclass, replace

from vtuber.domain import Turn, TurnId, TurnRemembered
from vtuber.kernel import EventBus


@dataclass(frozen=True, slots=True)
class Branch:
    """Ветка — путь до листа: `title` — последняя реплика; `active` — текущий путь через неё."""

    leaf: TurnId
    title: str
    length: int
    active: bool


@dataclass(frozen=True, slots=True)
class Checkpoint:
    """Названное место в диалоге."""

    name: str
    turn: TurnId


class DialogueTree:
    """Хранит все ходы; история промпта — только путь до активного.

    Приватные ходы сюда не попадают: они забываются вместе с режимом (S-17.2). Дерево живёт в
    памяти: на диске все ходы остаются подряд в заметке чата (ADR-0020), разметка веток — нет.
    """

    def __init__(self) -> None:
        self._turns: dict[TurnId, Turn] = {}
        self._parents: dict[TurnId, TurnId | None] = {}
        self._active: TurnId | None = None
        self._checkpoints: dict[str, TurnId] = {}

    @property
    def active(self) -> TurnId | None:
        """Ход, к которому будет дописан следующий."""
        return self._active

    def follow(self, bus: EventBus) -> None:
        """Подписка на записанные ходы."""
        bus.subscribe(TurnRemembered, self._on_turn)

    async def _on_turn(self, event: TurnRemembered) -> None:
        if not event.turn.is_private:
            self.add(event.turn)

    def seed(self, turns: Iterable[Turn]) -> None:
        """Разговор прошлого запуска: своих номеров у таких ходов нет, даём отрицательные."""
        for index, turn in enumerate(turns, start=1):
            self.add(replace(turn, id=TurnId(-index)))

    def add(self, turn: Turn) -> None:
        """Дописывает ход к активному."""
        self._turns[turn.id] = turn
        self._parents[turn.id] = self._active
        self._active = turn.id

    def path(self) -> tuple[Turn, ...]:
        """Ходы от начала до активного."""
        return self._path_to(self._active)

    def go(self, turn: TurnId) -> tuple[Turn, ...]:
        """Делает ход активным; следующая реплика начнёт новую ветку.

        Raises:
            ValueError: такого хода нет.

        """
        if turn not in self._turns:
            msg = f"В диалоге нет такой реплики: {turn}"
            raise ValueError(msg)
        self._active = turn
        return self.path()

    def checkpoint(self, name: str) -> None:
        """Запомнить текущее место под именем.

        Raises:
            ValueError: имя пустое или диалог ещё не начат.

        """
        if not name.strip() or self._active is None:
            msg = "Контрольной точке нужны имя и хотя бы одна реплика"
            raise ValueError(msg)
        self._checkpoints[name.strip()] = self._active

    def checkpoints(self) -> tuple[Checkpoint, ...]:
        """Контрольные точки по имени."""
        return tuple(Checkpoint(name, turn) for name, turn in sorted(self._checkpoints.items()))

    def branches(self) -> tuple[Branch, ...]:
        """Ветки по листьям, в порядке создания."""
        parents = set(self._parents.values())
        return tuple(
            Branch(
                leaf,
                self._turns[leaf].user_text,
                len(self._path_to(leaf)),
                self._active in {turn.id for turn in self._path_to(leaf)},
            )
            for leaf in self._turns
            if leaf not in parents
        )

    def _path_to(self, turn: TurnId | None) -> tuple[Turn, ...]:
        path: list[Turn] = []
        current = turn
        while current is not None:
            path.append(self._turns[current])
            current = self._parents[current]
        path.reverse()
        return tuple(path)
