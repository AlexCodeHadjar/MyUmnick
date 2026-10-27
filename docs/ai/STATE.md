# STATE — снимок проекта
_Обновлено: 2026-10-27, сессия S-2.4_

## Сейчас
- Этап: 2 — LLM: адаптер, стриминг, выбор модели (docs/stages/STAGE_02.md)
- Следующая сессия: **S-2.5 — прогон кандидатов и ADR-0004 выбора модели** — только на целевой
  машине (RTX 5070 Ti): нужны настоящий llama-server и 3–5 GGUF-моделей.
- Ветка: `main` (удалённого репозитория нет)

## Готово на этапе
- [x] S-2.1 Порт LLM, FakeLLM, контрактный тест
- [x] S-2.2 Адаптер OpenAI-совместимого API (httpx, SSE)
- [x] S-2.3 Адаптер llama.cpp, prefill, `scripts/start_llm.ps1` — кроме прогона `-m gpu`
- [x] S-2.4 `tools/bench_latency.py`, `tools/eval_quality.py`, 40 реплик, 50 кейсов — кроме
  прогона против настоящего сервера
- [ ] S-2.5

## Последние метрики
- `span()`: ≈ 1.2–1.5 мкс на замер (машина разработки).
- TTFT/TPS настоящей модели — ещё нет (S-2.5). Заглушка: TTFT p50 4.5 мс — это только накладные
  расходы ядра и HTTP на localhost.

## Открытые проблемы
- [P1] Не проверено на настоящем llama-server (целевая машина): `scripts/start_llm.ps1`,
  `uv run pytest -m gpu`, `n_ctx` на слот в `GET /slots`, поля `id_slot`/`chat_template_kwargs`
  в `/v1/chat/completions`; бенчмарк и eval против реальной модели.
- [P1] Лицензия Live2D: «Expandable Application» — публикация требует соглашения с Live2D даже
  для частных лиц (docs/licenses.md). ADR в S-6.1.
- [P2] Голоса: Silero — CC BY-NC; коммерчески чистые русские — Piper `denis`/`dmitri` (CC0).
- [P3] Выбор адаптера по конфигу (`Registry`, `[llm].backend`; пока словарь `BACKENDS` в
  `tools/llm_client.py`), прогрев при старте, `configure_logging`, логи и трассы,
  `Telemetry.run` — сборка в `bootstrap` (S-3.5).
- [P3] Системный промпт бенчмарка и eval — временный (`tools/llm_client.py`); заменить
  PromptBuilder после S-3.1.
- [P3] Текст ошибок pydantic в `ConfigError` — на английском.
- [P3] `tools/gen_map.py` не показывает модульные константы и `type`/`NewType`-псевдонимы.
- [P3] R-06 (импорт в обход `__init__`) не автоматизирован — только ревью.
- [P3] uv через `pip --user`: `C:\Users\Alast\AppData\Roaming\Python\Python312\Scripts` не в PATH.
- [P3] Node.js/pnpm не установлены — нужны с Этапа 5.

## Важно помнить
- Целевое железо: RTX 5070 Ti 16 ГБ VRAM, 32 ГБ RAM (Blackwell → llama.cpp с CUDA 12.8+).
- Файлы — всегда `encoding="utf-8"`: на Windows по умолчанию cp1251 (тест поймал это в бенчмарке).
- `.ps1` — только UTF-8 **с BOM** (Windows PowerShell 5.1).
- eval: `honesty` читать вместе с `knowledge` — «всегда не знаю» даёт 100 % честности.
- `main` скриптов `tools/` синхронная (`asyncio.run` внутри); в async-тестах — через
  `asyncio.to_thread`, чтобы заглушка жила в цикле теста.
- Новая зависимость — ADR. ADR-0004 — выбор LLM (S-2.5); следующий свободный — ADR-0008.

## Последний журнал
docs/ai/sessions/2026-10-27_S-2.4.md
