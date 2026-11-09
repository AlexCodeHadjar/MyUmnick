# bootstrap — корень композиции: конфиг, персона, сборка графа объектов, точка входа

## Ответственность
Единственное место, где создаются и связываются объекты приложения (ADR-0001), и граница
чтения файлов настроек. Читает конфиг и персону, открывает файлы логов и трасс, собирает реестр
LLM-адаптеров и движков TTS и сервис хода, прогревает кэш промпта и загружает голос, запускает терминальный чат или шлюз UI. Бизнес-логики
не содержит.

## Публичный API (`__init__.py`)
| Символ | Назначение |
|---|---|
| `AppConfig` | Корень конфига: `edition`, `logging`, `telemetry`, `llm`, `persona`, `context`, `gateway`, `pipeline`, `tts`, `scheduler`, `memory`, `stt`, `plugins`, `resources`, `llama_server`, `setup`, `supervisor` |
| `load_app_config(root, env, edition=ru)` | Конфиг издания из `<root>/config` поверх `env`; `[edition].id` сверяется с `edition` |
| `EditionConfig`, `resolve_edition`, `edition_files`, `ignored_user_keys`, `LANGUAGE_BOUND_KEYS` (`bootstrap/edition.py`) | Издание (ADR-0032): `--edition` / `VTUBER_EDITION__ID` / `ru`; файлы слоёв; языковые ключи общего `user.toml`, которые вне `ru` не действуют |
| `PersonaConfig`, `load_persona(path)` | `[persona].file` → доменная `Persona`; ошибки — `ConfigError` |
| `llm_backends()` | Реестр LLM-адаптеров: `llamacpp`, `openai_compat` (одна строка на адаптер) |
| `tts_backends()` | Реестр движков TTS: `silero`, `piper`, `voice_server` (откат на Silero, ADR-0031), `none` (без голоса) |
| `Core(bus, telemetry)`, `Backends(llm, tts, fillers=None)`, `build_conversation(cfg, persona, backends, core) → Conversation` | Сборка сервиса хода (с голосом — `Voice` с междометиями); `Conversation` — `service`, `prompts` (прогрев), `history` (фоновая память) |
| `MemoryConfig` | Секция `[memory]`: `enabled`, `store_path`, `background_slot_id`, `generation`, `facts`, `e5`; `resolved(root)` |
| `background_memory(cfg, history, bus)` (`bootstrap/memory.py`) | Фоновая память на время работы: LLM слота `background_slot_id`, e5, sqlite-vec, `IdleScheduler`, `MemoryKeeper` |
| `running_plugins(cfg, bus, discover)` (`bootstrap/plugins.py`) | Включённые плагины на время работы: entry points `vtuber.plugins`, сбой плагина — только лог (`docs/plugins.md`) |
| `LlmSupervised`, `TtsSupervised`, `build_voice`, `with_voice` (`bootstrap/supervision.py`) | Что поднимает наблюдатель и голос с обёрткой (ADR-0021) |
| `main(argv, env, console)`, `run()`, `Console`, `LineSource` | `python -m vtuber [chat или serve] [--root] [--edition]`; коды 0 / 1 (конфиг) / 2 (LLM недоступна в чате) |

## Зависимости
- Всё (верхний слой): kernel, domain, application, adapters/llm, adapters/tts, gateway.

## События
- Подписывает `TraceWriter` на `MetricRecorded`; запускает `Telemetry.run` в `TaskGroup`.

## Инварианты
- В `AppConfig` нет умолчаний: всё приходит из `config/default.toml`; он и
  `personas/default.toml` всегда валидны (`tests/unit/bootstrap/`).
- Неизвестный `[llm].backend` — `ConfigError` со списком доступных, код 1.
- Голос — только в режиме `serve` (терминал звук не воспроизводит); `[tts].backend` из реестра,
  неизвестный — `ConfigError`. Пути моделей — от `--root`. Модель грузится после старта шлюза:
  статус TTS `loading → ready | failed` (проба коротким синтезом); без модели ход идёт без звука.
- Старт: прогрев префикса промпта (T-06) со статусом LLM `loading → ready | failed` на шине.
  Чат: LLM недоступна — код 2. Сервер: поднимается до прогрева (UI видит статус), при недоступной
  LLM продолжает работать; живёт, пока открыт stdin (родитель Tauri умер — pipe закрыт — выход).
- Логи — через `kernel.logging_to`: настройка сбрасывается раньше, чем закрывается файл.
- Файлы логов и трасс открываются до `asyncio.run` и живут до выхода; пути — от `--root`.
- Сквозные тесты против заглушки сервера: `tests/integration/test_terminal_app.py`, `test_serve_app.py`.

## Как расширять
- Новый модуль со своей секцией → поле в `AppConfig` + секция в `config/default.toml`.
- Новый LLM-адаптер → строка `add` в `llm_backends()`.
- Новая персона — файл в `personas/` и путь в `[persona].file` (FR-11).
- Новый режим запуска — значение `mode` в `_parse` и ветка в `_run`.

## Связанные документы
ADR-0001, ADR-0005, ADR-0006, ADR-0007, ADR-0032
