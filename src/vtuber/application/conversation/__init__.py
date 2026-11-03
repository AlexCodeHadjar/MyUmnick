"""Сценарий «ход диалога»: реплика → промпт → конвейер → история и события."""

from vtuber.application.conversation.branches import Branch, Checkpoint, DialogueTree
from vtuber.application.conversation.service import INTERNAL_ERROR_MESSAGE, ConversationService

__all__ = [
    "INTERNAL_ERROR_MESSAGE",
    "Branch",
    "Checkpoint",
    "ConversationService",
    "DialogueTree",
]
