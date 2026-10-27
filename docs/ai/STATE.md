# STATE — снимок проекта
_Обновлено: 2026-10-27, сессия S-2.3_

## Сейчас
- Этап: 2 — LLM: адаптер, стриминг, выбор модели (docs/stages/STAGE_02.md)
- Следующая сессия: **S-2.4 — бенчмарк задержки и eval-заготовка**
- Ветка: `main` (удалённого репозитория нет)

## Готово на этапе
- [x] S-2.1 Порт LLM, FakeLLM, контрактный тест
- [x] S-2.2 Адаптер OpenAI-совместимого API (httpx, SSE)
- [x] S-2.3 Адаптер llama.cpp, prefill, `scripts/start_llm.ps1` — кроме прогона `-m gpu`
- [ ] S-2.4, S-2.5

## Последние метрики
- `span()`: ≈ 1.2–1.5 мкс на замер (машина разработки). TTFT — в S-2.4.

## Открытые проблемы
- [P1] Не проверено на настоящем llama-server (нужна целевая машина): `scripts/start_llm.ps1`
  с установленной версией, `uv run pytest -m gpu` (ответ без `<think>`, слот свободен после
  отмены), `n_ctx` на слот в `GET /slots`; принимает ли `/v1/chat/completions` поля `id_slot`
  и `chat_template_kwargs` (в README описаны только для `/completion`).
- [P1] Лицензия Live2D: «Expandable Application» — публикация требует соглашения с Live2D даже
  для частных лиц (docs/licenses.md). ADR в S-6.1.
- [P2] Голоса: Silero — CC BY-NC; коммерчески чистые русские — Piper `denis`/`dmitri` (CC0).
- [P3] Выбор адаптера по конфигу (`Registry`, `[llm].backend`), прогрев при старте (вызов
  `prefill` с системным промптом), `configure_logging`, файлы логов и трасс, `Telemetry.run` —
  сборка в `bootstrap` (S-3.5).
- [P3] Текст ошибок pydantic в `ConfigError` — на английском.
- [P3] `tools/gen_map.py` не показывает модульные константы и `type`/`NewType`-псевдонимы.
- [P3] R-06 (импорт в обход `__init__`) не автоматизирован — только ревью.
- [P3] uv через `pip --user`: `C:\Users\Alast\AppData\Roaming\Python\Python312\Scripts` не в PATH.
- [P3] Node.js/pnpm не установлены — нужны с Этапа 5.

## Важно помнить
- Целевое железо: RTX 5070 Ti 16 ГБ VRAM, 32 ГБ RAM (Blackwell → llama.cpp с CUDA 12.8+).
- `.ps1` — только UTF-8 **с BOM**: Windows PowerShell 5.1 читает файл без BOM как ANSI, и
  кириллица с «—» ломает строки.
- `LlamaCppLLM(OpenAICompatLLM)` переопределяет `_request_body` и `prefill`; новый HTTP-адаптер —
  в `http_adapters` контрактной фабрики.
- `tests/llm_stub.py` отвечает на `/v1/chat/completions` (SSE), `/v1/models`, `/apply-template`,
  `/completion`; `stub.bodies(path)`.
- Новая зависимость — ADR. ADR-0004 — выбор LLM (S-2.5); следующий свободный — ADR-0008.

## Последний журнал
docs/ai/sessions/2026-10-27_S-2.3.md
