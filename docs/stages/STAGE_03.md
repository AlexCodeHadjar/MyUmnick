# Этап 3 — Диалоговый сервис: персона, промпт, краткосрочная память, отмена

## Цель
Сценарий «ход диалога» целиком, пока без голоса и UI. Веха M1: диалог с персоной в терминале
с выводом TTFT после каждого ответа (`uv run python -m vtuber`).

## Зависимости
Этап 2.

## Критерии приёмки этапа
- [x] Префикс промпта (всё до истории) байт-в-байт одинаков на всех ходах; история между
      усечениями только растёт (`test_prefix_is_stable`, `test_short_term.py`).
- [x] Новая реплика или `/stop` прерывает ответ ≤ 100 мс (тест сервиса с фейком; на реальной
      модели — проверка M1). Ctrl+C завершает чат целиком.
- [x] Теги эмоций не попадают в выводимый текст (StreamParser, property-тест).
- [x] Персона меняется правкой TOML без изменения кода (FR-11).

## Подводные камни
- Время/дата в системном промпте ломает кэш (T-03). Динамика — только в последнем блоке.

## Сессии

### S-3.1 — Персона и PromptBuilder
- **Цель:** `personas/default.toml` (шаблон `docs/templates/persona.toml`) и загрузка в Persona;
  `PromptBuilder` строит промпт «от неизменного к изменчивому», список эмоций — из Emotion.
- **Scope:** `src/vtuber/application/prompting/`, `personas/`, `domain/dialogue.py` (если нужны
  поля); загрузчик персоны — `bootstrap/persona.py` (чтение файла — граница, не application)
- **Читать:** карточка `domain`, `docs/performance.md` (T-03, T-07)
- **Готово, когда:**
  - [x] Тест порядка блоков; тест `test_prefix_is_stable` (байтовое сравнение между ходами).
  - [x] Персона из `personas/default.toml` загружается в `Persona`; ошибки — `ConfigError`.
- **Статус:** готова (журнал: `docs/ai/sessions/2026-10-27_S-3.1.md`)

### S-3.2 — Бюджет контекста и краткосрочная память
- **Цель:** `ContextBudget` (токены через `/tokenize` сервера или приближённо с калибровкой),
  `ShortTermMemory` (только дописывание, блочное усечение с местом под резюме, T-04).
- **Scope:** `application/prompting/context_budget.py`, `application/memory/short_term.py`
- **Читать:** карточка `application/prompting`, `docs/performance.md` (T-04)
- **Готово, когда:**
  - [x] Тест: при превышении лимита отрезается блок `trim_ratio`, а не одно сообщение.
  - [x] Property-тест: чередование ролей, бюджет, новый ход не отрезается, счёт токенов.
- **Статус:** готова (журнал: `docs/ai/sessions/2026-10-27_S-3.2.md`)

### S-3.3 — StreamParser
- **Цель:** разбор потока: теги эмоций → события, `display_text`/`spoken_text`/`full_text`.
- **Scope:** `application/pipeline/stream_parser.py`
- **Читать:** `docs/architecture.md` (StreamParser), карточка `domain`
- **Готово, когда:**
  - [x] Тесты: тег, разрезанный между дельтами; неизвестный тег выброшен; property-based —
        склейка display_text == вход без тегов.
  - [x] «<» не в форме тега остаётся текстом; недописанный тег в конце потока выбрасывается.
- **Статус:** готова (журнал: `docs/ai/sessions/2026-10-27_S-3.3.md`)

### S-3.4 — ReplyPipeline (текстовая ветка)
- **Цель:** порт `ReplySink` и фейк `RecordingSink` (записи с отметками времени из
  `FakeClock`); `deliver(sink)` у событий разбора (`TextDelta`, `EmotionCue`); конвейер
  LLM → StreamParser → sink; TTS-ветка — через NullTTS до Этапа 7.
- **Scope:** `ports/sink.py`, `tests/fakes/`, `application/pipeline/reply_pipeline.py`
- **Читать:** `docs/architecture.md` (Конвейер ответа)
- **Готово, когда:**
  - [x] Тест с FakeLLM и RecordingSink: дельты в sink до конца генерации; отмена останавливает
        LLM-стрим.
- **Статус:** готова (журнал: `docs/ai/sessions/2026-10-27_S-3.4.md`)

### S-3.5 — ConversationService, отмена, CLI
- **Цель:** жизненный цикл хода (Enum + таблица переходов), отмена предыдущего хода, события,
  запись в историю только показанного; терминальный чат; сборка в bootstrap.
- **Scope:** `application/conversation/`, `domain/turn_state.py`, `gateway/terminal.py`,
  `bootstrap/` (`container.py`, `main.py`), `vtuber/__main__.py`, конфиг `[llm.generation]`,
  `[telemetry]`, `[logging].file`. Точка входа — `python -m vtuber`: gateway не может импортировать
  bootstrap, поэтому `python -m vtuber.gateway.cli` из плана невозможен по слоям.
- **Читать:** `docs/architecture.md` (Жизненный цикл хода, Корень композиции)
- **Готово, когда:**
  - [x] Недопустимый переход состояния — исключение (тест).
  - [x] Сквозной тест приложения против заглушки: ответ, TTFT, прогрев, логи и трассы в файлах.
  - [ ] **На целевой машине:** ручная проверка M1 с реальной моделью — стриминг, TTFT,
        прерывание ≤ 100 мс.
- **Статус:** готова, кроме ручной проверки M1 (журнал: `docs/ai/sessions/2026-10-27_S-3.5.md`)
