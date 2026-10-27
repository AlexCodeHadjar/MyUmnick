# STATE — снимок проекта
_Обновлено: 2026-10-27, сессия S-2.2_

## Сейчас
- Этап: 2 — LLM: адаптер, стриминг, выбор модели (docs/stages/STAGE_02.md)
- Следующая сессия: **S-2.3 — адаптер llama.cpp, прогрев, скрипт запуска**
- Ветка: `main` (удалённого репозитория нет)

## Готово на этапе
- [x] S-2.1 Порт LLM, FakeLLM, контрактный тест
- [x] S-2.2 Адаптер OpenAI-совместимого API (httpx, SSE)
- [ ] S-2.3 … S-2.5

## Последние метрики
- `span()`: ≈ 1.2–1.5 мкс на замер (машина разработки). TTFT — в S-2.4.

## Открытые проблемы
- [P1] Лицензия Live2D: «Expandable Application» — публикация требует соглашения с Live2D даже
  для частных лиц (docs/licenses.md). ADR в S-6.1.
- [P2] Голоса: Silero — CC BY-NC; коммерчески чистые русские — Piper `denis`/`dmitri` (CC0).
- [P3] Выбор адаптера по конфигу (`Registry`, поле `[llm].backend`), `configure_logging`, файлы
  логов и трасс, `Telemetry.run` — сборка в `bootstrap` (S-3.5).
- [P3] Текст ошибок pydantic в `ConfigError` — на английском.
- [P3] `tools/gen_map.py` не показывает модульные константы и `type`/`NewType`-псевдонимы.
- [P3] R-06 (импорт в обход `__init__`) не автоматизирован; внутренний `adapters/llm/sse.py`
  импортируется тестами напрямую — это допустимо для тестов модуля.
- [P3] uv через `pip --user`: `C:\Users\Alast\AppData\Roaming\Python\Python312\Scripts` не в PATH.
- [P3] Node.js/pnpm не установлены — нужны с Этапа 5.

## Важно помнить
- Целевое железо: RTX 5070 Ti 16 ГБ VRAM, 32 ГБ RAM (Blackwell → llama.cpp с CUDA 12.8+).
- LLM-адаптеры — асинхронные контекстные менеджеры (`async with OpenAICompatLLM(cfg) as llm`);
  `LLMCase` в контрактной фабрике отдаёт `AbstractAsyncContextManager[LLMPort]`.
- `tests/llm_stub.py` — сервер-заглушка SSE на localhost (`requests`, `client_gone`).
- На Windows `asyncio.sleep(0.002)` ≈ 15 мс, а закрытый порт отвечает не сразу — в тестах крупные
  порции и `connect_timeout_s=0.2`.
- Новая зависимость — ADR. ADR-0004 — выбор LLM (S-2.5); следующий свободный — ADR-0008.

## Последний журнал
docs/ai/sessions/2026-10-27_S-2.2.md
