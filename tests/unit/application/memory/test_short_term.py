from hypothesis import given
from hypothesis import strategies as st

from vtuber.application.memory import INTERRUPTED_MARK, ShortTermMemory
from vtuber.application.prompting import ContextBudget, ContextConfig
from vtuber.domain import Message, Role, Turn, TurnId

# chars_per_token=1 и без накладных расходов: токены = символы — так проще считать в тестах.
BUDGET = ContextBudget(
    ContextConfig(
        max_history_tokens=100, trim_ratio=0.5, chars_per_token=1, message_overhead_tokens=0
    )
)


def _turn(number: int, size: int = 5, *, interrupted: bool = False) -> Turn:
    return Turn(TurnId(number), "u" * size, "a" * size, is_interrupted=interrupted)


def test_turns_become_alternating_user_and_assistant_messages() -> None:
    memory = ShortTermMemory(BUDGET)

    memory.append(Turn(TurnId(1), "Привет", "<happy>Привет!"))

    assert memory.messages == (
        Message(Role.USER, "Привет"),
        Message(Role.ASSISTANT, "<happy>Привет!"),
    )


def test_interrupted_reply_is_kept_with_mark() -> None:
    memory = ShortTermMemory(BUDGET)

    memory.append(Turn(TurnId(1), "Расскажи", "Жила-была", is_interrupted=True))
    memory.append(Turn(TurnId(2), "Стоп", "", is_interrupted=True))

    replies = [m.text for m in memory.messages if m.role is Role.ASSISTANT]
    assert replies == [f"Жила-была{INTERRUPTED_MARK}", INTERRUPTED_MARK]


def test_history_only_grows_while_under_budget() -> None:
    memory = ShortTermMemory(BUDGET)
    previous: tuple[Message, ...] = ()

    for number in range(10):  # 10 ходов по 10 токенов = ровно лимит
        assert memory.append(_turn(number)) == ()
        assert memory.messages[: len(previous)] == previous
        previous = memory.messages


def test_overflow_cuts_a_whole_block_of_oldest_turns_not_one_message() -> None:
    memory = ShortTermMemory(BUDGET)
    for number in range(10):
        memory.append(_turn(number))

    dropped = memory.append(_turn(10))

    assert len(dropped) == 12  # 6 старших ходов: 110 → 50 токенов
    assert memory.tokens == 50
    assert memory.messages[0].role is Role.USER
    assert dropped[0].role is Role.USER


def test_cache_breaks_rarely_over_a_long_conversation() -> None:
    memory = ShortTermMemory(BUDGET)

    trims = sum(1 for number in range(100) if memory.append(_turn(number)))

    assert trims <= 100 // 5  # после усечения до следующего — минимум 5 ходов


def test_newest_turn_is_never_dropped_even_if_it_alone_exceeds_budget() -> None:
    memory = ShortTermMemory(BUDGET)
    memory.append(_turn(1))

    memory.append(_turn(2, size=80))

    assert memory.messages == (Message(Role.USER, "u" * 80), Message(Role.ASSISTANT, "a" * 80))


@given(st.lists(st.integers(min_value=0, max_value=60), max_size=60))
def test_invariants_hold_for_any_conversation(sizes: list[int]) -> None:
    memory = ShortTermMemory(BUDGET)

    for number, size in enumerate(sizes):
        memory.append(_turn(number, size))

        messages = memory.messages
        assert memory.tokens == BUDGET.tokens(messages)
        assert memory.tokens <= BUDGET.max_history_tokens or len(messages) == 2
        roles = [message.role for message in messages]
        assert roles == [Role.USER, Role.ASSISTANT] * (len(messages) // 2)
        assert messages[-2:] == (
            Message(Role.USER, "u" * size),
            Message(Role.ASSISTANT, "a" * size),
        )
