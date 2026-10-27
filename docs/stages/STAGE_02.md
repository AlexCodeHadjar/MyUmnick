# Этап 2 — LLM: адаптер, стриминг, выбор модели

## Цель
Подключить локальную LLM с потоковой генерацией, измерить скорость и выбрать модель по данным,
а не по отзывам.

## Зависимости
Этап 1.

## Критерии приёмки этапа
- [ ] TTFT p50 ≤ 250 мс на коротком промпте при прогретом кэше (RTX 5070 Ti).
- [ ] Отмена посреди генерации останавливает работу сервера (логи llama-server / загрузка GPU).
- [ ] Модель выбрана по таблице ADR-0004: максимум качества при TTFT и TPS в бюджете.

## Подводные камни
- Некоторые модели в шаблоне чата добавляют системный промпт по умолчанию — проверить итоговый
  промпт через `/apply-template` (или аналог) llama-server.
- Не измерять TTFT на первом запросе после старта — для холодного старта отдельная метрика.
- RTX 5070 Ti — Blackwell (sm_120): нужна сборка llama.cpp с CUDA 12.8+.
- Лицензия модели — в `docs/licenses.md` до выбора.

## Сессии

### S-2.1 — Порт, фейк, контрактный тест
- **Цель:** `LLMPort` + `GenerationParams`; `FakeLLM(text, chunk_size, delay_ms)` с отказом на
  N-м токене; контрактный тест LLM.
- **Scope:** `src/vtuber/ports/llm.py`, `tests/fakes/fake_llm.py`, `tests/contract/`
- **Читать:** `docs/architecture.md` (Порты), `docs/testing.md` (Контрактные тесты)
- **Готово, когда:**
  - [x] Контракт: стрим отдаёт строки; отмена закрывает поток ≤ 50 мс; недоступный сервер →
        LLMUnavailable. FakeLLM проходит.
- **Статус:** готова (журнал: `docs/ai/sessions/2026-10-27_S-2.1.md`)

### S-2.2 — Адаптер OpenAI-совместимого API
- **Цель:** `OpenAICompatLLM`: `/v1/chat/completions` со `stream: true`, разбор SSE,
  тайм-ауты, перевод ошибок в доменные, закрытие потока при отмене.
- **Scope:** `src/vtuber/adapters/llm/openai_compat.py`, карточка `adapters/llm/README.md`,
  `tests/contract/factories.py` (новый `LLMCase`), секция конфига `[llm]`, ADR на httpx
- **Читать:** карточка `ports`, ADR-0002
- **Готово, когда:**
  - [x] Контрактный тест проходит (сервер-заглушка на localhost; «недоступный» — закрытый порт).
  - [x] Проверено, что после отмены заглушка видит закрытие соединения (T-14).
  - [x] httpx-исключения не выходят за адаптер (R-43).
- **Статус:** готова (журнал: `docs/ai/sessions/2026-10-27_S-2.2.md`)

### S-2.3 — Адаптер llama.cpp, прогрев, скрипт запуска
- **Цель:** `LlamaCppLLM` (слот `id_slot`, `cache_prompt`, `prefill()` — можно заглушкой до
  Этапа 9), отключение reasoning-режима (T-08), прогрев при старте (T-06), `scripts/start_llm.ps1`.
- **Scope:** `src/vtuber/adapters/llm/llamacpp.py`, `scripts/`, `tests/contract/factories.py`
  (`LLMCase` на заглушке `tests/llm_stub.py`), `tests/unit/adapters/llm/`
- **Читать:** карточка `adapters/llm`, `docs/performance.md` (T-06, T-08, T-10)
- **Заметка:** строится поверх `OpenAICompatLLM` (тот же httpx-клиент и разбор SSE). Тест `@gpu`
  выполняется на целевой машине (RTX 5070 Ti); здесь — заглушка и MockTransport.
- **Готово, когда:**
  - [x] Скрипт `scripts/start_llm.ps1` собран; флаги сверены с README llama-server (2026-10-27):
        `--n-gpu-layers 99 --ctx-size 16384 --parallel 2 --flash-attn on --jinja
        --reasoning-budget 0 --metrics --no-webui`.
  - [x] `LlamaCppLLM`: слот, `cache_prompt`, `chat_template_kwargs`, настоящий `prefill`
        (`/apply-template` → `/completion` с `n_predict: 0`); контракт LLM на заглушке.
  - [ ] **На целевой машине:** запуск скрипта с установленной версией (`llama-server --help`),
        `uv run pytest -m gpu` — ответ без `<think>`, слот освобождается после отмены (T-14);
        проверить `n_ctx` на слот в `GET /slots`.
- **Статус:** готова, кроме прогона на целевой машине (журнал: `docs/ai/sessions/2026-10-27_S-2.3.md`)

### S-2.4 — Бенчмарк задержки и eval-заготовка
- **Цель:** `tools/bench_latency.py` (TTFT, TPS, p50/p95), `bench/prompts_ru.jsonl` (30–50
  реплик), `eval/qa_ru.jsonl` (первые 50 вопросов), базовый `tools/eval_quality.py`.
- **Scope:** `tools/bench_latency.py`, `tools/eval_quality.py`, `bench/`, `eval/`, `tests/tools/`
- **Читать:** `docs/performance.md` (Как измеряем), `docs/testing.md` (Оценка качества)
- **Готово, когда:**
  - [x] Бенчмарк прогоняется против FakeLLM и HTTP-адаптера (заглушка), выводит p50/p95/max.
  - [x] eval выдаёт таблицу по категориям и список непройденных.
  - [ ] **На целевой машине:** оба скрипта против настоящего llama-server (вместе с S-2.5).
- **Статус:** готова, кроме прогона на целевой машине (журнал: `docs/ai/sessions/2026-10-27_S-2.4.md`)

### S-2.5 — Прогон кандидатов, ADR выбора модели
- **Цель:** 3–5 кандидатов 8–14B с сильным русским × Q4_K_M/Q5_K_M; ADR-0004 с таблицей
  «Модель | Квант | VRAM | TTFT p50 | TPS | Качество (eval) | Русский 1–5 | Лицензия | Решение».
- **Scope:** `docs/adr/0004-llm-model-choice.md`, `config/default.toml`, `docs/licenses.md`
- **Готово, когда:**
  - [ ] Таблица заполнена замерами на RTX 5070 Ti; порог качества для Этапа 10 зафиксирован.
- **Статус:** не начата
