from vtuber.domain import Message, Persona, Role, Turn, TurnId


def test_roles_match_chat_api_names() -> None:
    assert [role.value for role in Role] == ["system", "user", "assistant"]


def test_turn_is_complete_unless_marked_interrupted() -> None:
    turn = Turn(id=TurnId(1), user_text="Привет", reply_text="Привет-привет!")

    assert not turn.is_interrupted


def test_persona_has_no_examples_by_default() -> None:
    persona = Persona(
        name="Мика",
        language="ru",
        description="Виртуальная ведущая.",
        speech_style="Коротко.",
        rules=("Отвечай 1–3 предложениями.",),
    )

    assert persona.examples == ()


def test_messages_with_same_role_and_text_are_equal() -> None:
    assert Message(Role.USER, "Привет") == Message(Role.USER, "Привет")
