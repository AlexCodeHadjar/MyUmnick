"""Реплики зрителей — вне долговременной памяти (FR-31): факты и резюме пишутся только о ведущем."""

from collections.abc import Sequence

from vtuber.domain import Message, Role, is_viewer_line


def without_viewer_turns(messages: Sequence[Message]) -> tuple[Message, ...]:
    """Без реплик зрителей и ответов на них: иначе зритель попал бы в резюме, а оно — в промпт."""
    kept: list[Message] = []
    skip_answer = False
    for message in messages:
        if message.role is Role.USER and is_viewer_line(message.text):
            skip_answer = True
            continue
        if not (skip_answer and message.role is Role.ASSISTANT):
            kept.append(message)
        skip_answer = False
    return tuple(kept)
