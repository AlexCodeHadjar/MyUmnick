# PROJECT MAP

> Автогенерация: `python tools/gen_map.py`. Не редактировать.

## src/vtuber
Ядро локального ИИ-витюбера.

## src/vtuber/adapters
Адаптеры: реализации портов для конкретных движков.

## src/vtuber/adapters/llm
Адаптеры языковых моделей (LLMPort).

- `LlamaCppOptions` — `src/vtuber/adapters/llm/config.py:8` — Подсекция `[llm.llamacpp]`: особенности llama-server.
- `GenerationConfig` — `src/vtuber/adapters/llm/config.py:19` — Подсекция `[llm.generation]`: длина и температура ответа диалога (T-07).
- `LLMConfig` — `src/vtuber/adapters/llm/config.py:26` — Какой бэкенд, где он, тайм-ауты (R-36) и параметры генерации.
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

## src/vtuber/application/conversation
Сценарий «ход диалога»: реплика → промпт → конвейер → история и события.

- `ConversationService` — `src/vtuber/application/conversation/service.py:42` — Точка входа сценария «ход диалога» (docs/architecture.md, жизненный цикл хода).

## src/vtuber/application/memory
Память витюбера: история текущего разговора (далее — долговременная память, Этап 10).

- `ShortTermMemory` — `src/vtuber/application/memory/short_term.py:21` — История ходов для промпта (T-04).

## src/vtuber/application/pipeline
Конвейер ответа: LLM → разбор тегов → нарезка фраз → TTS.

- `ReplyPipeline` — `src/vtuber/application/pipeline/reply_pipeline.py:12` — Стримит ответ LLM получателю по мере генерации (T-01): ни одна стадия не ждёт конца.
- `TextDelta` — `src/vtuber/application/pipeline/stream_parser.py:20` — Порция текста: `text` — для чата, `spoken_text` — для TTS (без эмодзи и разметки).
- `EmotionCue` — `src/vtuber/application/pipeline/stream_parser.py:32` — В ответе встретился тег эмоции; озвучивать нечего.
- `StreamParser` — `src/vtuber/application/pipeline/stream_parser.py:46` — Разбирает дельты одного ответа по мере поступления (один экземпляр на ход).

## src/vtuber/application/prompting
Сборка промпта: персона, история, динамический блок — от неизменного к изменчивому (T-03).

- `ContextConfig` — `src/vtuber/application/prompting/context_budget.py:12` — Секция `[context]`.
- `ContextBudget` — `src/vtuber/application/prompting/context_budget.py:26` — Приближённый счёт токенов — без запроса к серверу, чтобы не тормозить горячий путь.
- `Prompt` — `src/vtuber/application/prompting/prompt_builder.py:14` — Сообщения для LLM; первые `prefix_length` — неизменный префикс (персона и примеры).
- `PromptBuilder` — `src/vtuber/application/prompting/prompt_builder.py:21` — Строит промпт: [персона + примеры] → [история] → [справка + реплика] (T-03).
- `render_system_prompt` — `src/vtuber/application/prompting/prompt_builder.py:45` — Системный промпт персоны; `{emotions}` в правилах → теги всех эмоций из `Emotion`.

## src/vtuber/bootstrap
Корень композиции: конфиг, персона, сборка графа объектов и точка входа.

- `AppConfig` — `src/vtuber/bootstrap/config.py:12` — Корень конфига. Только агрегирует: каждую секцию описывает модуль, которому она нужна.
- `load_app_config` — `src/vtuber/bootstrap/config.py:22` — Читает `config/default.toml` и `config/user.toml` из корня проекта `root` поверх `env`.
- `Core` — `src/vtuber/bootstrap/container.py:17` — Общие механизмы, которые получают все: шина событий и телеметрия.
- `llm_backends` — `src/vtuber/bootstrap/container.py:24` — Реестр LLM-адаптеров: имя из `[llm].backend` → адаптер (асинхронный контекстный менеджер).
- `build_conversation` — `src/vtuber/bootstrap/container.py:35` — Собирает сервис хода; `PromptBuilder` отдаётся и наружу — для прогрева кэша (T-06).
- `Console` — `src/vtuber/bootstrap/main.py:25` — Ввод построчно в отдельном потоке — ожидание строки не блокирует цикл (R-34).
- `main` — `src/vtuber/bootstrap/main.py:38` — Код возврата: 0 — чат завершён, 1 — ошибка конфига, 2 — LLM-сервер недоступен.
- `run` — `src/vtuber/bootstrap/main.py:86` — Запуск из консоли: `python -m vtuber [--root путь]`.
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
- `TurnStateError` — `src/vtuber/domain/errors.py:32` — Недопустимый переход состояния хода — ошибка в логике сервиса, а не во внешнем мире.
- `CancelReason` — `src/vtuber/domain/events.py:10` — Почему ход прерван.
- `Component` — `src/vtuber/domain/events.py:18` — Бэкенд, о состоянии которого сообщается в UI.
- `BackendState` — `src/vtuber/domain/events.py:25` — Состояние бэкенда для статус-бара UI.
- `TurnStarted` — `src/vtuber/domain/events.py:34` — Ход начат: аватар сразу показывает «думаю» (T-17).
- `TurnFinished` — `src/vtuber/domain/events.py:41` — Ход завершён полностью.
- `TurnCancelled` — `src/vtuber/domain/events.py:48` — Ход прерван; UI сбрасывает аудиобуфер. `message` — что сказать пользователю при ошибке.
- `EmotionChanged` — `src/vtuber/domain/events.py:57` — В ответе встретился тег эмоции.
- `MetricRecorded` — `src/vtuber/domain/events.py:65` — Замер стадии хода; `turn_id` — None, если замер вне хода (например, прогрев).
- `BackendStatusChanged` — `src/vtuber/domain/events.py:74` — Бэкенд загрузился, упал или восстановился.
- `AudioFormat` — `src/vtuber/domain/speech.py:11` — Формат звука: PCM s16le, моно — так звук передаётся в UI (ADR-0003).
- `AudioChunk` — `src/vtuber/domain/speech.py:23` — Непрерывный фрагмент PCM в формате `format`.
- `TurnState` — `src/vtuber/domain/turn_state.py:10` — Где сейчас ход: ждём реплику, думаем, говорим, прерваны.
- `next_state` — `src/vtuber/domain/turn_state.py:30` — Возвращает `target`, если переход из `current` разрешён.

## src/vtuber/gateway
Шлюз: интерфейсы к ядру — терминальный чат (M1), далее WebSocket-сервер для UI (Этап 4).

- `TerminalSink` — `src/vtuber/gateway/terminal.py:21` — ReplySink для консоли: печатает ответ по мере генерации и помнит время первой порции.
- `TerminalChat` — `src/vtuber/gateway/terminal.py:55` — Цикл чата: строка → ход; новая строка во время ответа прерывает его (T-14).

## src/vtuber/kernel
Общие механизмы ядра: шина событий, реестр, телеметрия, конфиг, логи.

- `EventBus` — `src/vtuber/kernel/bus.py:15` — Доставляет событие подписчикам его точного типа (не подклассов), параллельно.
- `ConfigSection` — `src/vtuber/kernel/config.py:21` — База секции конфига: неизменяема, лишний ключ — ошибка (опечатка не пройдёт молча).
- `ConfigFiles` — `src/vtuber/kernel/config.py:32` — Файлы конфигурации: `default` обязателен, `user` — если существует.
- `load_config` — `src/vtuber/kernel/config.py:45` — Собирает конфиг из файлов и окружения и проверяет его моделью `model`.
- `current_turn` — `src/vtuber/kernel/context.py:14` — Номер текущего хода или None вне хода; чтение — десятки наносекунд (горячий путь).
- `turn_context` — `src/vtuber/kernel/context.py:20` — Внутри блока ход `turn_id` — текущий для метрик, а логи несут поле `turn_id`.
- `LoggingConfig` — `src/vtuber/kernel/logging.py:14` — Секция `[logging]`; `file` открывает bootstrap (относительно корня проекта).
- `configure_logging` — `src/vtuber/kernel/logging.py:21` — Настраивает structlog: одна JSON-строка на событие в `stream`.
- `get_logger` — `src/vtuber/kernel/logging.py:41` — Логгер модуля; имя попадает в поле `module` каждого события.
- `Registry` — `src/vtuber/kernel/registry.py:8` — Имя → фабрика `A → T`; например, `Registry[TTSConfig, TTSPort]` для движков TTS.
- `TelemetryConfig` — `src/vtuber/kernel/telemetry.py:23` — Секция `[telemetry]`; `traces_file` открывает bootstrap (относительно корня проекта).
- `Telemetry` — `src/vtuber/kernel/telemetry.py:29` — Замеряет стадии хода и отдаёт метрики в шину фоновой задачей `run`.
- `Span` — `src/vtuber/kernel/telemetry.py:63` — Контекстный менеджер одного замера; создаётся `Telemetry.span`.
- `TraceWriter` — `src/vtuber/kernel/telemetry.py:88` — Подписчик шины: пишет каждую метрику JSON-строкой в поток (`logs/traces.jsonl`).

## src/vtuber/ports
Порты: Protocol-интерфейсы, через которые ядро обращается к внешнему миру.

- `GenerationParams` — `src/vtuber/ports/llm.py:11` — Параметры генерации; значения приходят из конфига (`[llm.generation]`, ADR-0006).
- `LLMPort` — `src/vtuber/ports/llm.py:19` — Локальная LLM; адаптеры бросают только доменные ошибки (R-43).
- `ReplySink` — `src/vtuber/ports/sink.py:8` — Получатель результатов одного хода; конвейер не знает, что за ним.
