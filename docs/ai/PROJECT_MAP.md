# PROJECT MAP

> Автогенерация: `python tools/gen_map.py`. Не редактировать.

## src/vtuber
Ядро локального ИИ-витюбера.

## src/vtuber/adapters
Адаптеры: реализации портов для конкретных движков.

## src/vtuber/adapters/llm
Адаптеры языковых моделей (LLMPort).

- `LlamaCppOptions` — `src/vtuber/adapters/llm/config.py:6` — Подсекция `[llm.llamacpp]`: особенности llama-server.
- `LLMConfig` — `src/vtuber/adapters/llm/config.py:17` — Адрес и тайм-ауты LLM-сервера (R-36).
- `LlamaCppLLM` — `src/vtuber/adapters/llm/llamacpp.py:21` — OpenAI-совместимый стрим + особенности llama-server.
- `OpenAICompatLLM` — `src/vtuber/adapters/llm/openai_compat.py:21` — Стрим ответа по HTTP/SSE; один httpx-клиент на всё время жизни (R-40, ADR-0007).
- `wire_messages` — `src/vtuber/adapters/llm/openai_compat.py:99` — Сообщения в формате OpenAI Chat API.
- `check_status` — `src/vtuber/adapters/llm/openai_compat.py:104` — Переводит HTTP-код ошибки в доменную: 503 (модель грузится) — недоступность, иное — сбой.
- `data_of` — `src/vtuber/adapters/llm/sse.py:12` — Полезная нагрузка строки `data: …` или None для пустых строк, комментариев и прочих полей.
- `delta_text` — `src/vtuber/adapters/llm/sse.py:19` — Текст дельты первого варианта ответа; пустая строка, если в порции текста нет.

## src/vtuber/adapters/memory
Адаптеры долговременной памяти: эмбеддеры и хранилища.

## src/vtuber/adapters/stt
Адаптеры распознавания речи (STTPort).

## src/vtuber/adapters/tts
Адаптеры синтеза речи (TTSPort).

## src/vtuber/application
Прикладной слой: сценарии диалога и конвейер ответа поверх портов.

## src/vtuber/application/memory
Память витюбера: история текущего разговора (далее — долговременная память, Этап 10).

- `ShortTermMemory` — `src/vtuber/application/memory/short_term.py:21` — История ходов для промпта (T-04).

## src/vtuber/application/prompting
Сборка промпта: персона, история, динамический блок — от неизменного к изменчивому (T-03).

- `ContextConfig` — `src/vtuber/application/prompting/context_budget.py:12` — Секция `[context]`.
- `ContextBudget` — `src/vtuber/application/prompting/context_budget.py:26` — Приближённый счёт токенов — без запроса к серверу, чтобы не тормозить горячий путь.
- `Prompt` — `src/vtuber/application/prompting/prompt_builder.py:14` — Сообщения для LLM; первые `prefix_length` — неизменный префикс (персона и примеры).
- `PromptBuilder` — `src/vtuber/application/prompting/prompt_builder.py:21` — Строит промпт: [персона + примеры] → [история] → [справка + реплика] (T-03).
- `render_system_prompt` — `src/vtuber/application/prompting/prompt_builder.py:40` — Системный промпт персоны; `{emotions}` в правилах → теги всех эмоций из `Emotion`.

## src/vtuber/bootstrap
Корень композиции: сборка графа объектов и точка входа.

- `AppConfig` — `src/vtuber/bootstrap/config.py:12` — Корень конфига. Только агрегирует: каждую секцию описывает модуль, которому она нужна.
- `load_app_config` — `src/vtuber/bootstrap/config.py:21` — Читает `config/default.toml` и `config/user.toml` из корня проекта `root` поверх `env`.
- `PersonaConfig` — `src/vtuber/bootstrap/persona.py:13` — Секция `[persona]`: путь к файлу персоны относительно корня проекта.
- `load_persona` — `src/vtuber/bootstrap/persona.py:33` — Читает и проверяет файл персоны; лишний или пропущенный ключ — ошибка.

## src/vtuber/domain
Доменный слой: неизменяемые сущности и значения диалога, речи и эмоций.

- `Role` — `src/vtuber/domain/dialogue.py:11` — Автор сообщения; значения совпадают с ролями OpenAI-совместимого API.
- `Message` — `src/vtuber/domain/dialogue.py:20` — Одно сообщение контекста LLM.
- `Turn` — `src/vtuber/domain/dialogue.py:28` — Завершённый ход: реплика пользователя и ответ витюбера.
- `Persona` — `src/vtuber/domain/dialogue.py:42` — Характер витюбера, задаётся файлом `personas/*.toml` без правки кода (FR-11).
- `Emotion` — `src/vtuber/domain/emotion.py:10` — Единственный источник списка эмоций: из него строятся промпт персоны и разбор ответа.
- `parse_tag` — `src/vtuber/domain/emotion.py:31` — Возвращает эмоцию по тегу вида `<happy>` или None, если тег неизвестен или искажён.
- `VtuberError` — `src/vtuber/domain/errors.py:4` — Базовая ошибка приложения; сообщение говорит, что делать (R-45).
- `BackendUnavailable` — `src/vtuber/domain/errors.py:8` — Бэкенд не отвечает или не загружен.
- `LLMUnavailable` — `src/vtuber/domain/errors.py:12` — LLM-сервер недоступен.
- `TTSUnavailable` — `src/vtuber/domain/errors.py:16` — Движок синтеза речи недоступен.
- `GenerationFailed` — `src/vtuber/domain/errors.py:20` — Бэкенд ответил, но генерация сорвалась посреди хода.
- `ProtocolError` — `src/vtuber/domain/errors.py:24` — Сообщение от UI не соответствует протоколу.
- `ConfigError` — `src/vtuber/domain/errors.py:28` — Конфигурация не читается или не проходит проверку; приложение не стартует.
- `CancelReason` — `src/vtuber/domain/events.py:10` — Почему ход прерван.
- `Component` — `src/vtuber/domain/events.py:18` — Бэкенд, о состоянии которого сообщается в UI.
- `BackendState` — `src/vtuber/domain/events.py:25` — Состояние бэкенда для статус-бара UI.
- `TurnStarted` — `src/vtuber/domain/events.py:34` — Ход начат: аватар сразу показывает «думаю» (T-17).
- `TurnFinished` — `src/vtuber/domain/events.py:41` — Ход завершён полностью.
- `TurnCancelled` — `src/vtuber/domain/events.py:48` — Ход прерван; UI сбрасывает аудиобуфер.
- `EmotionChanged` — `src/vtuber/domain/events.py:56` — В ответе встретился тег эмоции.
- `MetricRecorded` — `src/vtuber/domain/events.py:64` — Замер стадии хода; `turn_id` — None, если замер вне хода (например, прогрев).
- `BackendStatusChanged` — `src/vtuber/domain/events.py:73` — Бэкенд загрузился, упал или восстановился.
- `AudioFormat` — `src/vtuber/domain/speech.py:11` — Формат звука: PCM s16le, моно — так звук передаётся в UI (ADR-0003).
- `AudioChunk` — `src/vtuber/domain/speech.py:23` — Непрерывный фрагмент PCM в формате `format`.

## src/vtuber/gateway
Шлюз: WebSocket-сервер и протокол обмена с UI.

## src/vtuber/kernel
Общие механизмы ядра: шина событий, реестр, телеметрия, конфиг, логи.

- `EventBus` — `src/vtuber/kernel/bus.py:15` — Доставляет событие подписчикам его точного типа (не подклассов), параллельно.
- `ConfigSection` — `src/vtuber/kernel/config.py:21` — База секции конфига: неизменяема, лишний ключ — ошибка (опечатка не пройдёт молча).
- `ConfigFiles` — `src/vtuber/kernel/config.py:32` — Файлы конфигурации: `default` обязателен, `user` — если существует.
- `load_config` — `src/vtuber/kernel/config.py:45` — Собирает конфиг из файлов и окружения и проверяет его моделью `model`.
- `current_turn` — `src/vtuber/kernel/context.py:14` — Номер текущего хода или None вне хода; чтение — десятки наносекунд (горячий путь).
- `turn_context` — `src/vtuber/kernel/context.py:20` — Внутри блока ход `turn_id` — текущий для метрик, а логи несут поле `turn_id`.
- `LoggingConfig` — `src/vtuber/kernel/logging.py:13` — Секция `[logging]`.
- `configure_logging` — `src/vtuber/kernel/logging.py:19` — Настраивает structlog: одна JSON-строка на событие в `stream`.
- `get_logger` — `src/vtuber/kernel/logging.py:39` — Логгер модуля; имя попадает в поле `logger` каждого события.
- `Registry` — `src/vtuber/kernel/registry.py:8` — Имя → фабрика `A → T`; например, `Registry[TTSConfig, TTSPort]` для движков TTS.
- `Telemetry` — `src/vtuber/kernel/telemetry.py:21` — Замеряет стадии хода и отдаёт метрики в шину фоновой задачей `run`.
- `Span` — `src/vtuber/kernel/telemetry.py:55` — Контекстный менеджер одного замера; создаётся `Telemetry.span`.
- `TraceWriter` — `src/vtuber/kernel/telemetry.py:80` — Подписчик шины: пишет каждую метрику JSON-строкой в поток (`logs/traces.jsonl`).

## src/vtuber/ports
Порты: Protocol-интерфейсы, через которые ядро обращается к внешнему миру.

- `GenerationParams` — `src/vtuber/ports/llm.py:11` — Параметры генерации; значения приходят из конфига (`[llm.generation]`, ADR-0006).
- `LLMPort` — `src/vtuber/ports/llm.py:19` — Локальная LLM; адаптеры бросают только доменные ошибки (R-43).
