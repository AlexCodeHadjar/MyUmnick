"""Тексты фоновой памяти по языкам (Этап 20): промпты резюме и фактов, подписи, гейт поиска.

Русские — байт в байт прежние (golden-тест). Гейт — эвристики без модели (T-12): свои слова у языка.
"""

import re
from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class GatePatterns:
    """Эвристики гейта поиска: о прошлом, о пользователе, вопрос, вопрос о мире, «я» в вопросе."""

    recall: re.Pattern[str]
    about_user: re.Pattern[str]
    question: re.Pattern[str]
    factual: re.Pattern[str]
    me_as_subject: re.Pattern[str]


@dataclass(frozen=True, slots=True)
class MemoryTexts:
    """Строки фоновой памяти и справки хода."""

    summary_prompt: str
    extract_prompt: str
    user_label: str
    assistant_label: str
    previous_summary: str  # `{summary}`
    fragment: str
    facts_prefix: str
    summary_template: str  # `{summary}`, `{text}`
    gate: GatePatterns


def _re(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern, re.IGNORECASE)


RU_MEMORY: Final = MemoryTexts(
    summary_prompt="""\
Ты сжимаешь начало разговора пользователя с ассистентом, чтобы ассистент помнил его суть.
Напиши связный пересказ от третьего лица, 2–6 предложений: о чём говорили, что пользователь \
рассказал о себе, о чём договорились, что осталось недосказанным. Если дано прежнее резюме — \
включи его суть в новое. Без вступлений, списков и markdown — только текст пересказа.""",
    extract_prompt="""\
Ты ведёшь долговременную память ассистента о пользователе. Прочитай фрагмент диалога и выпиши \
новые факты о пользователе.
Факт — короткое утверждение от третьего лица: «Пользователя зовут Алексей», «Пользователь живёт \
в Казани», «Пользователь не любит хоррор-игры», «У пользователя в мае отпуск».
Записывай: имя, место, работу и учёбу, увлечения, что нравится и не нравится, планы, важные \
события, близких людей и питомцев.
Не записывай: что ассистент говорит о себе, приветствия, вопросы, догадки, сиюминутное \
(«пользователь поздоровался»).
importance: 1 — имя и главное о жизни, 0.5 — предпочтения и планы, 0.2 — мелочи.
Ответь только JSON без пояснений и без markdown: \
{"facts": [{"text": "…", "importance": 0.5}]}. Нет фактов — {"facts": []}.""",
    user_label="Пользователь",
    assistant_label="Ассистент",
    previous_summary="Прежнее резюме: {summary}",
    fragment="Фрагмент:",
    facts_prefix="Ты помнишь о пользователе:",
    summary_template="(Кратко о начале разговора: {summary})\n{text}",
    gate=GatePatterns(
        recall=_re(
            r"\b(помни\w*|вспомни\w*|забыл\w*|напомни\w*|говорил\w*|рассказывал\w*|упоминал\w*"
            r"|обсуждали|в прошлый раз|в прошлом разговоре|раньше)\b"
        ),
        about_user=_re(
            r"\b(я|мне|меня|мной|мой|моя|моё|мое|мою|мои|моего|моей|моих|моему|моим|моими|моём|моем"
            r"|у меня|обо мне)\b"
        ),
        question=_re(
            r"\?|\b(кто|что|чем|чего|где|куда|откуда|когда|как|какой|какая|какое|какие|сколько|почему"
            r"|зачем|знаешь|угадай|скажи|расскажи)\b"
        ),
        factual=_re(
            r"^\s*(кто|что такое|что значит|где|когда|сколько|какой|какая|какое|какие|почему|зачем"
            r"|в каком|в какой|на каком|на какой|чем отличается|как называется)\b"
        ),
        me_as_subject=_re(
            r"\b(как|что|кто|где|когда|сколько|куда)\b.*\b(я|меня|мне|мой|моя|моё|мою|мои|моего|моей)\b"
        ),
    ),
)

EN_MEMORY: Final = MemoryTexts(
    summary_prompt="""\
You compress the beginning of a conversation between the user and the assistant so the \
assistant remembers its gist. Write a coherent third-person retelling, 2–6 sentences: what was \
discussed, what the user said about themselves, what was agreed on, what was left unsaid. If a \
previous summary is given, fold its gist into the new one. No intros, lists or markdown — only \
the retelling. Write in English.""",
    extract_prompt="""\
You keep the assistant's long-term memory about the user. Read the dialogue fragment and write \
down new facts about the user.
A fact is a short third-person statement: "The user's name is Alex", "The user lives in \
Toronto", "The user dislikes horror games", "The user has a vacation in May".
Record: name, place, work and study, hobbies, likes and dislikes, plans, important events, \
close people and pets.
Do not record: what the assistant says about itself, greetings, questions, guesses, momentary \
things ("the user said hi").
importance: 1 — name and the main things in life, 0.5 — preferences and plans, 0.2 — trifles.
Write facts in English. Answer only with JSON, no explanations and no markdown: \
{"facts": [{"text": "…", "importance": 0.5}]}. No facts — {"facts": []}.""",
    user_label="User",
    assistant_label="Assistant",
    previous_summary="Previous summary: {summary}",
    fragment="Fragment:",
    facts_prefix="What you remember about the user:",
    summary_template="(Brief summary of the start of the conversation: {summary})\n{text}",
    gate=GatePatterns(
        recall=_re(
            r"\b(remember\w*|recall\w*|forgot\w*|remind\w*|told you|said before|mentioned"
            r"|we talked|we discussed|last time|earlier|before)\b"
        ),
        about_user=_re(r"\b(i|me|my|mine|myself|i'm|i've|i'd|about me)\b"),
        question=_re(r"\?|\b(who|what|which|where|when|why|how|do you know|guess|tell me)\b"),
        factual=_re(
            r"^\s*(who|what is|what are|what does|where|when|how many|how much|which|why"
            r"|what's the difference|how is it called)\b"
        ),
        me_as_subject=_re(r"\b(what|who|where|when|how|which)\b.*\b(i|me|my|mine|i'm)\b"),
    ),
)
