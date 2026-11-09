"""Русское издание после выноса текстов в пакет (S-20.2) — байт в байт как до него.

Эталон `tests/golden/ru_texts.json` снят с кода до правки; меняется только вместе с решением
изменить русские тексты (тогда эталон переснимается осознанно).
"""

import json
from pathlib import Path

from vtuber.adapters.llm.llamacpp import NO_FOREIGN_SCRIPTS_GRAMMAR
from vtuber.application.language import RU_PACK
from vtuber.application.prompting import PromptBuilder, render_system_prompt
from vtuber.bootstrap import load_persona
from vtuber.domain import RU_VIEWER, viewer_line

ROOT = Path(__file__).resolve().parents[4]
GOLDEN = json.loads((ROOT / "tests" / "golden" / "ru_texts.json").read_text(encoding="utf-8"))
SPEECH_SAMPLES = (
    "В 2024 году 15% людей, т.е. 3,5 млн.",
    "Привет, YouTube и Python!",
    "Цена $5 и 10 руб. №7 @мика",
)


def test_system_prompt_and_context_are_unchanged() -> None:
    persona = load_persona(ROOT / "personas" / "default.toml")
    builder = PromptBuilder(persona, RU_PACK.prompt)

    assert render_system_prompt(persona, RU_PACK.prompt) == GOLDEN["system_prompt"]
    assert builder.build((), "Привет", ("справка",)).messages[-1].text == GOLDEN["with_context"]


def test_service_lines_are_unchanged() -> None:
    texts = RU_PACK.prompt

    assert texts.image_note == GOLDEN["image_note"]
    assert texts.rewind_warmup == GOLDEN["rewind_warmup"]
    assert texts.warmup_user == GOLDEN["warmup_user"]
    assert texts.tts_probe == GOLDEN["tts_probe"]


def test_memory_texts_are_unchanged() -> None:
    memory = RU_PACK.memory

    assert memory.summary_prompt == GOLDEN["summary_prompt"]
    assert memory.extract_prompt == GOLDEN["extract_prompt"]
    assert memory.facts_prefix == GOLDEN["facts_prefix"]
    assert memory.summary_template == GOLDEN["summary_template"]


def test_diction_is_unchanged() -> None:
    diction = RU_PACK.diction

    assert sorted(diction.abbreviations) == GOLDEN["abbreviations"]
    assert [diction.normalize(text) for text in SPEECH_SAMPLES] == GOLDEN["speech"]


def test_viewer_line_and_grammar_are_unchanged() -> None:
    assert RU_VIEWER.prefix == GOLDEN["viewer_prefix"]
    assert viewer_line("Вася!", "привет [мика]", RU_PACK.prompt.viewer) == GOLDEN["viewer_line"]
    assert GOLDEN["grammar"] == NO_FOREIGN_SCRIPTS_GRAMMAR
