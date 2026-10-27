# bootstrap — корень композиции: конфиг, персона, сборка графа объектов, точка входа

## Ответственность
Единственное место, где создаются и связываются объекты приложения (ADR-0001), и граница
чтения файлов настроек. Читает конфиг и персону, открывает файлы логов и трасс, собирает реестр
LLM-адаптеров и сервис хода, прогревает кэш промпта, запускает терминальный чат. Бизнес-логики
не содержит.

## Публичный API (`__init__.py`)
| Символ | Назначение |
|---|---|
| `AppConfig` | Корень конфига: `logging`, `telemetry`, `llm`, `persona`, `context` |
| `load_app_config(root, env)` | Читает `<root>/config/default.toml` и `user.toml` поверх `env` |
| `PersonaConfig`, `load_persona(path)` | `[persona].file` → доменная `Persona`; ошибки — `ConfigError` |
| `llm_backends()` | Реестр LLM-адаптеров: `llamacpp`, `openai_compat` (одна строка на адаптер) |
| `Core(bus, telemetry)`, `build_conversation(cfg, persona, llm, core)` | Сборка сервиса хода и `PromptBuilder` |
| `main(argv, env, console)`, `run()`, `Console` | Точка входа `python -m vtuber`; коды 0 / 1 (конфиг) / 2 (LLM недоступна) |

## Зависимости
- Всё (верхний слой): kernel, domain, application, adapters/llm, gateway.

## События
- Подписывает `TraceWriter` на `MetricRecorded`; запускает `Telemetry.run` в `TaskGroup`.

## Инварианты
- В `AppConfig` нет умолчаний: всё приходит из `config/default.toml`; он и
  `personas/default.toml` всегда валидны (`tests/unit/bootstrap/`).
- Неизвестный `[llm].backend` — `ConfigError` со списком доступных, код 1.
- Старт: прогрев префикса промпта (`llm.prefill(prompts.prefix)`, T-06); LLM недоступна — код 2.
- Файлы логов и трасс открываются до `asyncio.run` и живут до выхода; пути — от `--root`.
- Сквозной тест `tests/integration/test_terminal_app.py` — против заглушки сервера.

## Как расширять
- Новый модуль со своей секцией → поле в `AppConfig` + секция в `config/default.toml`.
- Новый LLM-адаптер → строка `add` в `llm_backends()`.
- Новая персона — файл в `personas/` и путь в `[persona].file` (FR-11).
- Этап 4: режим WebSocket-сервера рядом с терминальным чатом.

## Связанные документы
ADR-0001, ADR-0005, ADR-0006, ADR-0007
