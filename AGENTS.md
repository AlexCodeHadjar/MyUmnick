# AI VTuber — инструкции для ИИ-ассистента

## Проект
Локальный ИИ-витюбер: Live2D-модель справа, чат слева, «мозг» — локальная LLM, работает офлайн.
Процессы: UI (Tauri + Svelte, `ui/`) ↔ WebSocket ↔ Ядро (Python 3.12 asyncio, `src/vtuber/`)
↔ HTTP/SSE ↔ llama-server. Основной язык общения витюбера — русский.
Целевое железо: RTX 5070 Ti 16 ГБ VRAM, 32 ГБ RAM.

## Приоритеты (строго по порядку)
1. Скорость ответа (TTFT, TTFA). 2. Правильность. 3. Расширяемость. 4. Внешний вид.

## Как работать (обязательно)
- Протокол сессии — `docs/ai/WORKFLOW.md`. Первое действие — прочитать `docs/ai/STATE.md`.
- НЕ читай репозиторий целиком. Порядок: STATE → `docs/stages/STAGE_NN.md` текущего этапа →
  `docs/ai/PROJECT_MAP.md` (поиском) → README.md модулей из scope → конкретные строки файлов.
  До начала правок — не больше ~6 документов.
- Меняй только файлы из scope сессии. Нужно больше — остановись и объясни.
- В конце сессии: проверки, карточки модулей, `gen_map`, журнал, перезапись STATE.md, галочки
  в STAGE, коммит после подтверждения.

## Правила кода
`docs/rules/code-rules.md` (R-01…R-71), ревью — `docs/rules/review-checklist.md`. Ключевое:
- Слои: domain ← ports ← application ← adapters | gateway ← bootstrap; kernel не зависит ни от
  кого. Контракты — `.importlinter`.
- Адаптеры создаются только в bootstrap. Зависимости — через конструктор.
- `mypy --strict`, без Any. Функция ≤ 20 инструкций, сложность ≤ 8, ≤ 4 аргументов,
  файл ≤ 250 строк кода.
- В корутинах нет блокирующих вызовов. CancelledError не подавлять. Внешние вызовы с тайм-аутом,
  ресурсы — через `async with`.
- Горячий путь (LLM → парсер → нарезка → TTS → sink) — очереди, не шина. Изменение → замер до/после.
- Комментарий объясняет «почему»; ссылайся на T-NN (`docs/performance.md`), R-NN, ADR-NNNN.

## Где что лежит
- Архитектура, протокол, жизненный цикл хода — `docs/architecture.md`
- Техники скорости T-01…T-17 и бюджет задержки — `docs/performance.md`
- Требования FR/NFR, железо — `docs/requirements.md`; стек — `docs/stack.md`
- Тесты, фейки, eval, риски — `docs/testing.md`; лицензии — `docs/licenses.md`
- Решения — `docs/adr/`; шаблоны — `docs/templates/`; обзор документации — `docs/README.md`

## Команды
- Установка: `uv sync`, затем `uv run pre-commit install`
- Тесты: `uv run pytest` (с покрытием: `--cov`; GPU-тесты: `-m gpu`)
- Все проверки: `uv run pre-commit run --all-files`
- Карта проекта: `uv run python tools/gen_map.py`
- Бенчмарк (с Этапа 2): `uv run python tools/bench_latency.py`
- LLM-сервер (с Этапа 2): `scripts/start_llm.ps1`
- UI (с Этапа 5): `cd ui && pnpm tauri dev`

## Запрещено
- Читать `models/`, `node_modules/`, `target/`, `logs/`, lock-файлы, `docs/archive/`.
- Править автогенерируемые файлы (`docs/ai/PROJECT_MAP.md`, `docs/protocol.md`,
  `ui/src/core/protocol.gen.ts`).
- Добавлять зависимости без ADR.
- Менять архитектурное решение без ADR.
