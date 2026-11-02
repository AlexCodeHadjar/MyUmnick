import json
from collections.abc import Sequence
from itertools import pairwise

from vtuber.application.prompting import PromptBuilder
from vtuber.domain import Emotion, Message, Persona, Role

PERSONA = Persona(
    name="Мика",
    language="русский",
    description="Дружелюбная виртуальная ведущая.",
    speech_style="Говорит живо и коротко.",
    rules=(
        "Отвечай 1–3 предложениями.",
        "Начинай ответ с тега эмоции. Доступные теги: {emotions}.",
    ),
    examples=(
        Message(Role.USER, "Привет!"),
        Message(Role.ASSISTANT, "<happy>Привет-привет!"),
    ),
)


def _wire(messages: Sequence[Message]) -> bytes:
    """Как промпт уходит на сервер — для байтового сравнения."""
    return json.dumps([[m.role.value, m.text] for m in messages], ensure_ascii=False).encode()


def test_system_prompt_describes_persona_and_lists_every_emotion_tag() -> None:
    system = PromptBuilder(PERSONA).build(history=(), user_text="Привет").messages[0]

    assert system.role is Role.SYSTEM
    for part in ("Мика", "Дружелюбная виртуальная ведущая.", "Говорит живо", "русский"):
        assert part in system.text
    assert "Отвечай 1–3 предложениями." in system.text
    assert all(emotion.tag in system.text for emotion in Emotion)
    assert "{emotions}" not in system.text


def test_blocks_go_from_stable_to_changing() -> None:
    history = (Message(Role.USER, "Как дела?"), Message(Role.ASSISTANT, "<happy>Отлично!"))

    prompt = PromptBuilder(PERSONA).build(history=history, user_text="Что делаешь?")

    roles_and_texts = [(m.role, m.text) for m in prompt.messages[1:]]
    assert roles_and_texts == [
        (Role.USER, "Привет!"),
        (Role.ASSISTANT, "<happy>Привет-привет!"),
        (Role.USER, "Как дела?"),
        (Role.ASSISTANT, "<happy>Отлично!"),
        (Role.USER, "Что делаешь?"),
    ]


def test_prefix_is_stable() -> None:
    builder = PromptBuilder(PERSONA)
    history: list[Message] = []
    prompts = []
    for turn, user_text in enumerate(("Привет", "Как дела?", "Пока!")):
        prompts.append(builder.build(history=tuple(history), user_text=user_text))
        history += [Message(Role.USER, user_text), Message(Role.ASSISTANT, f"Ответ {turn}")]

    prefix = _wire(prompts[0].messages[: prompts[0].prefix_length])
    assert all(_wire(p.messages[: p.prefix_length]) == prefix for p in prompts)
    # История между ходами только дописывается: каждый промпт без последней реплики —
    # начало следующего.
    for current, following in pairwise(prompts):
        assert following.messages[: len(current.messages) - 1] == current.messages[:-1]


def test_dynamic_context_goes_only_into_current_user_message() -> None:
    builder = PromptBuilder(PERSONA)

    plain = builder.build(history=(), user_text="Который час?")
    with_context = builder.build(history=(), user_text="Который час?", context=("Сейчас 21:40.",))

    assert with_context.messages[:-1] == plain.messages[:-1]
    last = with_context.messages[-1]
    assert last.role is Role.USER
    # Реплика — первой: её начало общее с прогревом черновика и историей (T-05).
    assert last.text.startswith("Который час?")
    assert "Сейчас 21:40." in last.text


def test_persona_without_examples_has_only_system_prefix() -> None:
    persona = Persona(name="Мика", language="русский", description="", speech_style="", rules=())

    prompt = PromptBuilder(persona).build(history=(), user_text="Привет")

    assert prompt.prefix_length == 1
    assert [m.role for m in prompt.messages] == [Role.SYSTEM, Role.USER]
