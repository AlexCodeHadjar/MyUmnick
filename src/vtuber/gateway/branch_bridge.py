"""Ветки диалога ↔ UI (S-16.1): после перехода UI получает путь активной ветки целиком."""

from collections.abc import Awaitable, Callable

from vtuber.application.conversation import ConversationService, DialogueTree
from vtuber.application.pipeline import StreamParser, TextDelta
from vtuber.domain import Turn, TurnId, without_viewer_prefix
from vtuber.gateway.protocol import OutboundMessage, turn_ref
from vtuber.gateway.protocol_branches import (
    BranchCheckpoint,
    BranchData,
    BranchGo,
    BranchMessageData,
    BranchState,
    CheckpointData,
)


def shown_text(reply: str) -> str:
    """Ответ в истории хранится с тегами эмоций; в чате их быть не должно."""
    parser = StreamParser()
    events = (*parser.feed(reply), *parser.flush())
    return "".join(event.text for event in events if isinstance(event, TextDelta))


def _parse_turn(ref: str) -> TurnId:
    """`t-000042` → 42; у восстановленных ходов номер отрицательный."""
    try:
        return TurnId(int(ref.removeprefix("t-")))
    except ValueError as exc:
        msg = f"Неверный номер реплики: {ref}"
        raise ValueError(msg) from exc


def _messages(turn: Turn) -> list[BranchMessageData]:
    ref = turn_ref(turn.id)
    user = without_viewer_prefix(turn.user_text)
    return [
        BranchMessageData(role="user", text=user, turn=None),
        BranchMessageData(role="assistant", text=shown_text(turn.reply_text), turn=ref),
    ]


class BranchBridge:
    """Переход отменяет идущий ответ и заменяет историю промпта: модель видит только новую ветку."""

    def __init__(
        self,
        service: ConversationService,
        tree: DialogueTree,
        send: Callable[[OutboundMessage], Awaitable[None]],
    ) -> None:
        self._service = service
        self._tree = tree
        self._send = send

    async def send_state(self, *, always: bool = False) -> None:
        """Окно перезапустилось или диалог восстановлен: показать то, что знает ядро.

        `always` — и пустой разговор тоже: после смены чата окно должно очистить чужую историю.
        """
        if always or self._tree.active is not None:
            await self._send_state(None)

    async def handle(self, message: BranchGo | BranchCheckpoint) -> None:
        """Перейти к реплике или поставить контрольную точку; ошибка показывается рядом."""
        problem = None
        try:
            if isinstance(message, BranchGo):
                await self._go(_parse_turn(message.data.turn))
            else:
                self._tree.checkpoint(message.data.name)
        except ValueError as exc:
            problem = str(exc)
        await self._send_state(problem)

    async def _go(self, turn: TurnId) -> None:
        # Сначала отмена: прерванный ответ должен дописаться в старую ветку, а не в новую.
        await self._service.stop_current()
        await self._service.rewind(self._tree.go(turn))

    async def _send_state(self, problem: str | None) -> None:
        messages = [message for turn in self._tree.path() for message in _messages(turn)]
        branches = [
            BranchData(
                leaf=turn_ref(branch.leaf),
                title=without_viewer_prefix(branch.title),
                length=branch.length,
                active=branch.active,
            )
            for branch in self._tree.branches()
        ]
        checkpoints = [
            CheckpointData(name=point.name, turn=turn_ref(point.turn))
            for point in self._tree.checkpoints()
        ]
        await self._send(BranchState.of(messages, branches, checkpoints, problem))
