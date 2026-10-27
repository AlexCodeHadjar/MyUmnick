# STATE — снимок проекта
_Обновлено: 2026-10-27, сессия S-3.3_

## Сейчас
- Этап: 3 — Диалоговый сервис (docs/stages/STAGE_03.md)
- Следующая сессия: **S-3.4 — ReplySink, RecordingSink, ReplyPipeline (текстовая ветка)**
- **S-2.5 отложена** до целевой машины (RTX 5070 Ti): прогон 3–5 GGUF-моделей и ADR-0004.
- Ветка: `main` (удалённого репозитория нет)

## Готово
- [x] Этапы 0, 1; Этап 2 — S-2.1…S-2.4 (кроме прогонов на целевой машине)
- [x] S-3.1 Персона (`personas/default.toml`, `bootstrap.load_persona`) и `PromptBuilder`
- [x] S-3.2 `ContextBudget` (секция `[context]`) и `ShortTermMemory` (усечение блоком, T-04)
- [x] S-3.3 `StreamParser`: `TextDelta`/`EmotionCue`, `full_text` для истории
- [ ] S-3.4, S-3.5

## Последние метрики
- `span()`: ≈ 1.2–1.5 мкс на замер (машина разработки).
- TTFT/TPS настоящей модели — ещё нет (S-2.5).

## Открытые проблемы
- [P1] Не проверено на настоящем llama-server (целевая машина): `scripts/start_llm.ps1`,
  `uv run pytest -m gpu`, `n_ctx` на слот в `GET /slots`, поля `id_slot`/`chat_template_kwargs`
  в `/v1/chat/completions`; бенчмарк и eval против реальной модели; S-2.5.
- [P1] Лицензия Live2D: «Expandable Application» — публикация требует соглашения с Live2D даже
  для частных лиц (docs/licenses.md). ADR в S-6.1.
- [P2] Голоса: Silero — CC BY-NC; коммерчески чистые русские — Piper `denis`/`dmitri` (CC0).
- [P2] Справка (`context`) кладётся в текст текущей реплики: если история хранит реплику без
  справки, на следующем ходу llama-server пересчитает только последний ход (десятки токенов).
  Что хранить в истории — решить в S-3.5 (ConversationService).
- [P2] `chars_per_token = 3.0` — оценка «на глаз»; откалибровать по `/tokenize` выбранной модели
  (S-9.1), иначе история может не влезть в `n_ctx` слота или усекаться слишком рано.
- [P3] Резюме отрезанной истории не делается: отрезанное просто теряется до Этапа 10
  (`ShortTermMemory.append` уже возвращает его).
- [P3] Бенчмарк и eval (`tools/llm_client.py`) — со своим временным системным промптом; перевести
  на `render_system_prompt(load_persona(...))`.
- [P3] Выбор адаптера по конфигу (`Registry`, `[llm].backend`), прогрев при старте,
  `configure_logging`, логи и трассы, `Telemetry.run` — сборка в `bootstrap` (S-3.5).
- [P3] Текст ошибок pydantic в `ConfigError` — на английском.
- [P3] `tools/gen_map.py` не показывает модульные константы и `type`/`NewType`-псевдонимы.
- [P3] R-06 (импорт в обход `__init__`) не автоматизирован — только ревью.
- [P3] uv через `pip --user`: `C:\Users\Alast\AppData\Roaming\Python\Python312\Scripts` не в PATH.
- [P3] Node.js/pnpm не установлены — нужны с Этапа 5.

## Важно помнить
- Целевое железо: RTX 5070 Ti 16 ГБ VRAM, 32 ГБ RAM (Blackwell → llama.cpp с CUDA 12.8+).
- Префикс промпта собирается один раз в `PromptBuilder.__init__`; время и факты — только через
  `context` в последнюю реплику (T-03).
- В историю — `StreamParser.full_text` (с тегами `<happy>`), а не текст чата: модель видит свои
  ответы с тегами и продолжает их ставить. `StreamParser` — новый экземпляр на каждый ход.
- Персона: `[[examples]]` — массив пар; `{emotions}` подставляется из `Emotion`.
- Файлы — всегда `encoding="utf-8"`; `.ps1` — UTF-8 **с BOM**.
- Новая зависимость — ADR. ADR-0004 — выбор LLM (S-2.5); следующий свободный — ADR-0008.

## Последний журнал
docs/ai/sessions/2026-10-27_S-3.3.md
