"""Навыки (Этап 23, ADR-0043): реестр, встроенные навыки ядра, связь с плагинами и сервисом хода."""

from typing import Final

from vtuber.adapters.skills import JsonSkillChoices
from vtuber.application.conversation import ConversationService
from vtuber.application.skills import SkillRegistry
from vtuber.application.tools import ToolContext
from vtuber.bootstrap.config import AppConfig
from vtuber.bootstrap.plugins import PluginServices
from vtuber.domain import CORE_INITIATIVE, CORE_MEMORY, CORE_PLUGIN, SkillInfo

# Тексты встроенных навыков — на языке издания: панель показывает их как есть.
_CORE_TEXTS: Final = {
    "ru": {
        CORE_MEMORY: (
            "Память о вас",
            "Перед ответом вспоминает факты и заметки о вас",
            ("Как зовут мою собаку?",),
        ),
        CORE_INITIATIVE: (
            "Сама заговаривает",
            "Начинает разговор, когда вы долго молчите",
            (),
        ),
    },
    "en": {
        CORE_MEMORY: (
            "Memory about you",
            "Recalls facts and notes about you before answering",
            ("What's my dog's name?",),
        ),
        CORE_INITIATIVE: (
            "Starts conversations",
            "Speaks up on its own when you've been quiet for a while",
            (),
        ),
    },
}


def core_skills(cfg: AppConfig) -> tuple[SkillInfo, ...]:
    """Встроенные навыки: память всегда, инициатива — если она включена в конфиге."""
    texts = _CORE_TEXTS.get(cfg.edition.language, _CORE_TEXTS["ru"])
    wanted = [CORE_MEMORY] + ([CORE_INITIATIVE] if cfg.initiative.enabled else [])
    return tuple(
        SkillInfo(
            id=skill,
            plugin=CORE_PLUGIN,
            title=texts[skill][0],
            summary=texts[skill][1],
            examples=texts[skill][2],
        )
        for skill in wanted
    )


async def open_skills(cfg: AppConfig) -> SkillRegistry:
    """Реестр с выбором пользователя и встроенными навыками."""
    registry = await SkillRegistry.open(JsonSkillChoices(cfg.skills.file))
    registry.add(core_skills(cfg))
    return registry


def connect_skills(
    cfg: AppConfig, service: ConversationService, plugins: PluginServices, skills: SkillRegistry
) -> None:
    """Навыки плагинов — в реестр; справка хода — через гейт; плагин можно запустить на ходу.

    Без инструментов сервис хода не тратит на них ни одного вызова: справка подключается, когда
    появляется первый инструмент, в том числе у плагина, включённого из панели.
    """
    skills.add(plugins.skills)
    tools = ToolContext(plugins.contexts, cfg.plugins.context_timeout_s, skills)
    linked = False

    def link() -> None:
        nonlocal linked
        if plugins.contexts and not linked:
            service.use_tools(tools.hints)
            linked = True

    async def load(name: str) -> tuple[SkillInfo, ...] | None:
        loaded = await plugins.load(name)
        link()
        return loaded

    link()
    skills.load_plugin = load
