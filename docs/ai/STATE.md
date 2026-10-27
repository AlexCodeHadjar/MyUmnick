# STATE — снимок проекта
_Обновлено: 2026-10-27, сессия S-1.3_

## Сейчас
- Этап: 2 — LLM: адаптер, стриминг, выбор модели (docs/stages/STAGE_02.md)
- Следующая сессия: **S-2.1 — порт LLM, фейк, контрактный тест**
- Ветка: `main` (удалённого репозитория нет)

## Готово
- [x] Этап 0 — фундамент (кроме ручной проверки «≤ 6 файлов» в новой сессии)
- [x] Этап 1 — domain + kernel: S-1.1, S-1.2, S-1.3; все критерии приёмки выполнены

## Последние метрики
- `span()`: ≈ 1.2–1.5 мкс на замер (предел 5 мкс; `uv run pytest -m slow`), машина разработки.

## Открытые проблемы
- [P1] Лицензия Live2D: приложение, загружающее любые модели, — «Expandable Application»,
  публикация требует соглашения с Live2D даже для частных лиц (docs/licenses.md). ADR в S-6.1.
- [P2] Голоса: Silero — CC BY-NC; коммерчески чистые русские — Piper `denis`/`dmitri` (CC0).
- [P3] `configure_logging`, файлы `logs/app.jsonl` и `logs/traces.jsonl`, запуск `Telemetry.run`
  в TaskGroup — в `bootstrap/main.py` (S-3.5).
- [P3] Текст ошибок pydantic в `ConfigError` — на английском.
- [P3] `tools/gen_map.py` не показывает модульные константы и `type`/`NewType`-псевдонимы.
- [P3] R-06 (импорт в обход `__init__`) не автоматизирован — только ревью.
- [P3] uv через `pip --user`: `C:\Users\Alast\AppData\Roaming\Python\Python312\Scripts` не в PATH.
- [P3] Node.js/pnpm не установлены — нужны с Этапа 5.

## Важно помнить
- Целевое железо: RTX 5070 Ti 16 ГБ VRAM, 32 ГБ RAM (Blackwell → llama.cpp с CUDA 12.8+).
- Реестр: `Registry[A, T].add(name, factory)` в модуле адаптера, без декоратора (mypy не
  типизирует его без Any). `create(name, arg)`; неизвестное имя → `ConfigError`.
- Замеры: `Telemetry` внедряется через конструктор; `span()` только из потока event loop.
- ruff 0.17 форматирует код в .md: хук `ruff format` проверяет markdown, `--force-exclude`
  держит `docs/archive` нетронутым.
- Новая зависимость — ADR (S-2.2: httpx). ADR-0004 — выбор LLM (S-2.5); следующий свободный —
  ADR-0007.

## Последний журнал
docs/ai/sessions/2026-10-27_S-1.3.md
