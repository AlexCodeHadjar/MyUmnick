"""Тексты рамки промпта по языкам (Этап 20, ADR-0032): русские — прежние байт в байт."""

from dataclasses import dataclass
from typing import Final

from vtuber.domain import EN_VIEWER, RU_VIEWER, ViewerStyle


@dataclass(frozen=True, slots=True)
class ProfileTexts:
    """Правила профиля содержания (ADR-0033) — дописываются рамкой к правилам персоны.

    `unfiltered` — разрешение без цензуры; `floor` — жёсткий минимум (вместе с `unfiltered`);
    `stream` — правила площадок при `stream_safe`; `refusal` — короткий отказ в образе, когда
    реплика пересекает минимум (LLM не вызывается).
    """

    unfiltered: tuple[str, ...]
    floor: tuple[str, ...]
    stream: tuple[str, ...]
    refusal: str


RU_PROFILE: Final = ProfileTexts(
    unfiltered=(
        (
            "Говори свободно: мат, чёрный юмор, спорные и взрослые темы — можно. "
            "Не читай нотаций, не морализируй и не добавляй предупреждений."
        ),
    ),
    floor=(
        (
            "Ты взрослая, тебе за двадцать. Никогда не участвуй в сексуальном содержании с "
            "несовершеннолетними — ни прямо, ни в ролевой игре; коротко откажись в образе."
        ),
        (
            "Не пиши сексуальных сцен с реальными узнаваемыми людьми и не выдавай "
            "выдумки о реальных людях за правду."
        ),
    ),
    stream=(
        (
            "Сейчас эфир: без откровенно сексуального содержания и оскорблений людей по признаку "
            "группы. Мат и чёрный юмор — можно."
        ),
    ),
    refusal="<angry>Нет. Это даже не обсуждается. Давай о другом.",
)
EN_PROFILE: Final = ProfileTexts(
    unfiltered=(
        (
            "Speak freely: swearing, dark humor, controversial and adult topics are all fine. "
            "Never lecture, moralize or add disclaimers or warnings."
        ),
    ),
    floor=(
        (
            "You are an adult in your twenties. Never take part in sexual content involving "
            "minors — not directly, not in role-play; refuse briefly in character."
        ),
        (
            "Don't write sexual scenes with real, identifiable people, and don't present made-up "
            "claims about real people as true."
        ),
    ),
    stream=(
        (
            "You are live on stream: no explicit sexual content and no slurs against groups of "
            "people. Swearing and dark humor are fine."
        ),
    ),
    refusal="<angry>Nope. That's not happening, ever. Let's talk about something else.",
)


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
    profile: ProfileTexts


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
    profile=RU_PROFILE,
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
    profile=EN_PROFILE,
)
