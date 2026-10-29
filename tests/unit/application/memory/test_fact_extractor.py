"""Разбор ответов извлечения фактов (S-10.4): типичные ответы моделей — и кривые тоже.

Ответы ниже — в том виде, в каком их отдают локальные модели (обёртка ```json, пояснения,
лишние поля). Записанные ответы настоящей модели добавить на целевой машине (S-2.5).
"""

import pytest

from tests.fakes import FakeLLM
from vtuber.application.memory import FactExtractor, parse_facts
from vtuber.domain import GenerationFailed, Role, Turn, TurnId
from vtuber.ports import GenerationParams

PARAMS = GenerationParams(max_tokens=300, temperature=0.2)

GOOD_ANSWERS = [
    ('{"facts": [{"text": "Пользователя зовут Алексей", "importance": 1}]}', 1),
    ('```json\n{"facts": [{"text": "Пользователь живёт в Казани", "importance": 0.8}]}\n```', 1),
    (
        (
            'Вот факты:\n{"facts": [{"text": " Пользователь любит котов ", "importance": 0.5}, '
            '{"text": "У пользователя есть кот Барсик", "importance": 0.6, "category": "pets"}]}\n'
            "Надеюсь, помогла!"
        ),
        2,
    ),
    ('{"facts": []}', 0),
]

BAD_ANSWERS = [
    "Пользователь рассказал, что его зовут Алексей.",
    '{"facts": [{"text": "Пользователя зовут Алексей", "importance": 1}',
    "{'facts': [{'text': 'Пользователя зовут Алексей', 'importance': 1}]}",
    '{"facts": [{"text": "Алексей", "importance": 7}]}',
    '{"facts": "нет"}',
    '{"fact": []}',
    "",
]


@pytest.mark.parametrize(("raw", "count"), GOOD_ANSWERS)
def test_good_answers_are_parsed(raw: str, count: int) -> None:
    facts = parse_facts(raw)

    assert len(facts) == count
    assert all(fact.text == fact.text.strip() for fact in facts)


@pytest.mark.parametrize("raw", BAD_ANSWERS)
def test_bad_answers_are_generation_failed(raw: str) -> None:
    with pytest.raises(GenerationFailed):
        parse_facts(raw)


async def test_extractor_sends_dialogue_without_emotion_tags() -> None:
    llm = FakeLLM('{"facts": [{"text": "Пользователя зовут Алексей", "importance": 1}]}')

    facts = await FactExtractor(llm, PARAMS).extract(
        Turn(TurnId(3), "Меня зовут Алексей", "<happy>Приятно познакомиться!")
    )

    assert [fact.text for fact in facts] == ["Пользователя зовут Алексей"]
    (messages, params), *_ = llm.calls
    assert params == PARAMS
    assert messages[0].role is Role.SYSTEM
    assert messages[1].text == "Пользователь: Меня зовут Алексей\nАссистент: Приятно познакомиться!"
