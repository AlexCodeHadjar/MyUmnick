"""Участники и содержание диалога: роли, сообщения, ходы, персона."""

from dataclasses import dataclass
from enum import StrEnum
from typing import NewType

TurnId = NewType("TurnId", int)
"""Номер хода; в бинарном аудиокадре передаётся как uint64."""


class Role(StrEnum):
    """Автор сообщения; значения совпадают с ролями OpenAI-совместимого API."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True, slots=True)
class AttachedImage:
    """Картинка к реплике (S-18.1); только в памяти и на один ход."""

    mime: str
    base64: str


@dataclass(frozen=True, slots=True)
class Message:
    """Одно сообщение контекста LLM."""

    role: Role
    text: str
    images: tuple[AttachedImage, ...] = ()


@dataclass(frozen=True, slots=True)
class Turn:
    """Завершённый ход: реплика пользователя и ответ витюбера.

    У прерванного хода `reply_text` — только показанная/произнесённая часть, а `is_interrupted`
    истинно: модель должна «знать», что её перебили. `is_external` — реплика не от ведущего
    (зритель, таймер): о ведущем из неё ничего не узнать. `is_private` — приватный режим (S-17.2):
    на диск и в фоновую память такой ход не попадает.
    """

    id: TurnId
    user_text: str
    reply_text: str
    is_interrupted: bool = False
    is_external: bool = False
    is_private: bool = False


@dataclass(frozen=True, slots=True)
class Persona:
    """Характер витюбера, задаётся файлом `personas/*.toml` без правки кода (FR-11).

    Правила могут содержать плейсхолдер `{emotions}` — его подставляет построитель промпта
    из списка `Emotion`.
    """

    name: str
    language: str
    description: str
    speech_style: str
    rules: tuple[str, ...]
    examples: tuple[Message, ...] = ()
    initiative: str = ""
