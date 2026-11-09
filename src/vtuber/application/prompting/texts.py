"""Тексты рамки промпта по языкам (Этап 20, ADR-0032): русские — прежние байт в байт."""

from dataclasses import dataclass
from typing import Final

from vtuber.domain import EN_VIEWER, RU_VIEWER, ViewerStyle


@dataclass(frozen=True, slots=True)
class PromptTexts:
    """Строки рамки системного промпта и служебных реплик хода.

    `identity`, `speech_style`, `language` — шаблоны с `{name}`, `{style}`, `{language}`;
    `context` — справка после реплики (`{user_text}`, `{context}`): начало реплики остаётся общим
    с прогревом черновика (T-05); `warmup_user` — реплика прогрева кэша (T-06), `rewind_warmup` —
    прогрев после отката ветки; `tts_probe` — проба голоса после загрузки; `viewer` — подпись
    реплики зрителя (FR-31).
    """

    identity: str
    speech_style: str
    language: str
    rules_header: str
    context: str
    image_note: str
    warmup_user: str
    rewind_warmup: str
    tts_probe: str
    viewer: ViewerStyle


RU_PROMPT: Final = PromptTexts(
    identity="Ты — {name}.",
    speech_style="Манера речи: {style}",
    language="Язык общения: {language}.",
    rules_header="Правила:",
    context="{user_text}\n(Справка для тебя, пользователь её не видит: {context})",
    image_note="(показана картинка, сейчас её уже не видно)",
    warmup_user="Привет!",
    rewind_warmup="Продолжим.",
    tts_probe="Готова.",
    viewer=RU_VIEWER,
)

EN_PROMPT: Final = PromptTexts(
    identity="You are {name}.",
    speech_style="Speaking style: {style}",
    language="Language: {language}. Always answer in English only.",
    rules_header="Rules:",
    context="{user_text}\n(A note for you only, the user can't see it: {context})",
    image_note="(a picture was shown, it is no longer visible)",
    warmup_user="Hi!",
    rewind_warmup="Let's go on.",
    tts_probe="Ready.",
    viewer=EN_VIEWER,
)
