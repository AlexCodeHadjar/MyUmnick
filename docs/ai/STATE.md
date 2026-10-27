# STATE — снимок проекта
_Обновлено: 2026-10-27, сессия S-2.1_

## Сейчас
- Этап: 2 — LLM: адаптер, стриминг, выбор модели (docs/stages/STAGE_02.md)
- Следующая сессия: **S-2.2 — адаптер OpenAI-совместимого API (httpx, SSE)**
- Ветка: `main` (удалённого репозитория нет)

## Готово на этапе
- [x] S-2.1 Порт LLM, FakeLLM, контрактный тест
- [ ] S-2.2 … S-2.5

## Последние метрики
- `span()`: ≈ 1.2–1.5 мкс на замер (машина разработки).

## Открытые проблемы
- [P1] Лицензия Live2D: «Expandable Application» — публикация требует соглашения с Live2D даже
  для частных лиц (docs/licenses.md). ADR в S-6.1.
- [P2] Голоса: Silero — CC BY-NC; коммерчески чистые русские — Piper `denis`/`dmitri` (CC0).
- [P3] `configure_logging`, файлы логов и трасс, запуск `Telemetry.run` — `bootstrap/main.py`
  (S-3.5).
- [P3] Текст ошибок pydantic в `ConfigError` — на английском.
- [P3] `tools/gen_map.py` не показывает модульные константы и `type`/`NewType`-псевдонимы.
- [P3] R-06 (импорт в обход `__init__`) не автоматизирован — только ревью.
- [P3] uv через `pip --user`: `C:\Users\Alast\AppData\Roaming\Python\Python312\Scripts` не в PATH.
- [P3] Node.js/pnpm не установлены — нужны с Этапа 5.

## Важно помнить
- Целевое железо: RTX 5070 Ti 16 ГБ VRAM, 32 ГБ RAM (Blackwell → llama.cpp с CUDA 12.8+).
- Новый адаптер LLM = `LLMCase(name, available, unavailable)` в `tests/contract/factories.py` —
  контракт (`tests/contract/test_llm_contract.py`) прогонится для него автоматически.
- `FakeLLM(text, chunk_size, delay_ms, fail_after, error_type)`; `calls`/`prefills` — для
  проверки промптов в тестах Этапа 3.
- Реестр: `Registry[A, T].add(name, factory)` в модуле адаптера; `create(name, arg)`.
- Новая зависимость — ADR (S-2.2: httpx). ADR-0004 — выбор LLM (S-2.5); следующий свободный —
  ADR-0007.

## Последний журнал
docs/ai/sessions/2026-10-27_S-2.1.md
