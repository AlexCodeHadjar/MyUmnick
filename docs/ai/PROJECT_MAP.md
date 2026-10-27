# PROJECT MAP

> Автогенерация: `python -m tools.gen_map`. Не редактировать.

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

- `AppConfig` — `src/vtuber/bootstrap/config.py:13` — Корень конфига. Только агрегирует: каждую секцию описывает модуль, которому она нужна.
- `load_app_config` — `src/vtuber/bootstrap/config.py:24` — Читает `config/default.toml` и `config/user.toml` из корня проекта `root` поверх `env`.
- `Core` — `src/vtuber/bootstrap/container.py:17` — Общие механизмы, которые получают все: шина событий и телеметрия.
- `llm_backends` — `src/vtuber/bootstrap/container.py:24` — Реестр LLM-адаптеров: имя из `[llm].backend` → адаптер (асинхронный контекстный менеджер).
- `build_conversation` — `src/vtuber/bootstrap/container.py:35` — Собирает сервис хода; `PromptBuilder` отдаётся и наружу — для прогрева кэша (T-06).
- `LineSource` — `src/vtuber/bootstrap/main.py:38` — Откуда читать строки: `sys.stdin` или его тестовая замена.
- `Console` — `src/vtuber/bootstrap/main.py:45` — Ввод построчно в отдельном потоке — ожидание строки не блокирует цикл (R-34).
- `main` — `src/vtuber/bootstrap/main.py:58` — Код возврата: 0 — штатный выход, 1 — ошибка конфига, 2 — LLM недоступна (чат).
- `run` — `src/vtuber/bootstrap/main.py:153` — Запуск из консоли: `python -m vtuber [chat|serve] [--root путь]`.
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
Шлюз: протокол UI ↔ Ядро, кодек, WebSocket-сервер и терминальный чат (M1).

- `AudioFrame` — `src/vtuber/gateway/codec.py:20` — Разобранный аудиокадр.
- `decode_inbound` — `src/vtuber/gateway/codec.py:28` — Сообщение от UI; проверка один раз на границе (принцип 6 архитектуры).
- `encode_outbound` — `src/vtuber/gateway/codec.py:43` — JSON-строка сообщения для UI (сериализация pydantic-core, без лишних пробелов).
- `encode_audio_frame` — `src/vtuber/gateway/codec.py:48` — Бинарный кадр: 16 байт заголовка + PCM s16le моно; `seq` по модулю 2^16.
- `decode_audio_frame` — `src/vtuber/gateway/codec.py:56` — Разбирает аудиокадр (тесты; кадры микрофона — Этап 11).
- `turn_ref` — `src/vtuber/gateway/protocol.py:15` — Номер хода в JSON-сообщениях: `t-000042` (в аудиокадре — uint64).
- `ErrorCode` — `src/vtuber/gateway/protocol.py:20` — Что пошло не так — UI выбирает реакцию по коду, текст показывает пользователю.
- `EmptyData` — `src/vtuber/gateway/protocol.py:33` — Сообщение без полезной нагрузки.
- `SendData` — `src/vtuber/gateway/protocol.py:37` — Реплика пользователя.
- `DeltaData` — `src/vtuber/gateway/protocol.py:43` — Порция текста ответа.
- `EmotionData` — `src/vtuber/gateway/protocol.py:49` — Эмоция аватара; `intensity` 0…1 (затухание — Этап 8).
- `CancelledData` — `src/vtuber/gateway/protocol.py:56` — Почему ход прерван; `message` — текст ошибки при `reason == "error"`.
- `SpanData` — `src/vtuber/gateway/protocol.py:63` — Замер стадии хода для панели метрик (FR-15).
- `StatusData` — `src/vtuber/gateway/protocol.py:70` — Состояние бэкенда для статус-бара.
- `ErrorData` — `src/vtuber/gateway/protocol.py:77` — Ошибка для пользователя.
- `ChatSend` — `src/vtuber/gateway/protocol.py:84` — UI → Ядро: новая реплика; прерывает текущий ход.
- `ChatCancel` — `src/vtuber/gateway/protocol.py:92` — UI → Ядро: остановить ответ.
- `TurnStartedMessage` — `src/vtuber/gateway/protocol.py:103` — Ядро → UI: ход начат — аватар «думает» (T-17).
- `ChatDelta` — `src/vtuber/gateway/protocol.py:117` — Ядро → UI: порция текста ответа.
- `AvatarEmotion` — `src/vtuber/gateway/protocol.py:131` — Ядро → UI: сменить выражение аватара.
- `TurnFinishedMessage` — `src/vtuber/gateway/protocol.py:145` — Ядро → UI: ответ закончен полностью.
- `TurnCancelledMessage` — `src/vtuber/gateway/protocol.py:159` — Ядро → UI: ход прерван — UI сбрасывает аудиобуфер.
- `MetricsSpan` — `src/vtuber/gateway/protocol.py:173` — Ядро → UI: замер стадии; `turn` — None вне хода (прогрев).
- `Status` — `src/vtuber/gateway/protocol.py:187` — Ядро → UI: состояние бэкенда (вне хода).
- `ErrorMessage` — `src/vtuber/gateway/protocol.py:200` — Ядро → UI: ошибка; `turn` — None, если не относится к ходу (битое сообщение).
- `GatewayConfig` — `src/vtuber/gateway/server.py:44` — Секция `[gateway]`: где слушать UI (только localhost, ADR-0002).
- `GatewayServer` — `src/vtuber/gateway/server.py:51` — Шлюз для UI: `async with GatewayServer(...) as server: await server.serve_forever()`.
- `WsReplySink` — `src/vtuber/gateway/sink.py:12` — ReplySink для WebSocket: текст → `chat.delta`, эмоция → `avatar.emotion`.
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
- `LoggingConfig` — `src/vtuber/kernel/logging.py:16` — Секция `[logging]`; `file` открывает bootstrap (относительно корня проекта).
- `configure_logging` — `src/vtuber/kernel/logging.py:23` — Настраивает structlog: одна JSON-строка на событие в `stream`.
- `logging_to` — `src/vtuber/kernel/logging.py:45` — Логи идут в `stream` на время блока; на выходе — настройка по умолчанию.
- `get_logger` — `src/vtuber/kernel/logging.py:58` — Логгер модуля; имя попадает в поле `module` каждого события.
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

## ui/src/app
—

- `App.svelte` — `ui/src/app/App.svelte:1` — Окно: чат слева, сцена с аватаром справа (FR-01), статус-бар внизу, панель метрик по горячей
- `DEFAULT_RATIO` — `ui/src/app/split.ts:7` — Чат 2 : сцена 3 — как в каркасе S-5.1.
- `MIN_CHAT_PX` — `ui/src/app/split.ts:9` — Уже — чат не читается, сцена теряет модель.
- `MIN_STAGE_PX` — `ui/src/app/split.ts:10` — —
- `KEYBOARD_STEP` — `ui/src/app/split.ts:12` — Шаг стрелками на разделителе — доступность с клавиатуры.
- `RatioStorage` — `ui/src/app/split.ts:17` — Минимальное хранилище: в тестах — Map-подобная подмена.
- `clampRatio` — `ui/src/app/split.ts:20` — Доля в пределах, при которых обе панели не уже своего минимума.
- `ratioAt` — `ui/src/app/split.ts:30` — Доля по положению указателя внутри раскладки.
- `loadRatio` — `ui/src/app/split.ts:35` — Сохранённая доля или умолчание; битое значение или недоступное хранилище — умолчание.
- `saveRatio` — `ui/src/app/split.ts:45` — Запомнить долю; ошибка хранилища (переполнено, запрещено) не ломает раскладку.
- `SplitLayout.svelte` — `ui/src/app/SplitLayout.svelte:1` — Две панели с перетаскиваемым разделителем (FR-01). Доля — в split.ts: ограничение минимумами
- `Tone` — `ui/src/app/status.ts:8` — —
- `Indicator` — `ui/src/app/status.ts:10` — —
- `connectionIndicator` — `ui/src/app/status.ts:15` — —
- `backendIndicator` — `ui/src/app/status.ts:37` — Состояние бэкенда, пока связи нет, — устаревшее: показываем «—», а не последнее известное.
- `StatusBar.svelte` — `ui/src/app/StatusBar.svelte:1` — Статус-бар: связь с ядром и состояние бэкендов (LLM, TTS). Тексты и цвета — status.ts.

## ui/src/core
Публичный API core: фичи импортируют отсюда, а не из модулей пакета (R-63).

- `FrameScheduler` — `ui/src/core/batch.ts:8` — Запланировать вызов перед следующей отрисовкой; в окне — `requestAnimationFrame`.
- `animationFrame` — `ui/src/core/batch.ts:10` — —
- `FrameBatch` — `ui/src/core/batch.ts:20` — Очередь изменений до следующего кадра. Порядок сохраняется: смена связи и сообщения ядра идут
- `AudioSink` — `ui/src/core/client.ts:17` — —
- `CoreClientOptions` — `ui/src/core/client.ts:19` — —
- `CoreClient` — `ui/src/core/client.ts:28` — —
- `AUDIO_HEADER_SIZE` — `ui/src/core/frames.ts:11` — Заголовок аудиокадра `<BBHIQ`: тип, версия, seq, sample_rate, turn_id — docs/protocol.md.
- `AudioFrame` — `ui/src/core/frames.ts:17` — Аудиокадр ядра. `turn` — в том же виде, что в JSON-сообщениях, чтобы их сопоставлять.
- `FrameError` — `ui/src/core/frames.ts:25` — Кадр не соответствует протоколу: ядро другой версии или повреждённые данные.
- `turnRef` — `ui/src/core/frames.ts:45` — Номер хода из аудиокадра в виде JSON-сообщений.
- `parseMessage` — `ui/src/core/frames.ts:69` — Текстовый кадр → сообщение ядра; `FrameError`, если это не сообщение протокола.
- `decodeAudioFrame` — `ui/src/core/frames.ts:86` — Бинарный кадр → аудиокадр. PCM не копируется: `Int16Array` смотрит в тот же буфер
- `FIRST_CHAR_SPAN` — `ui/src/core/probe.ts:8` — —
- `FirstCharProbe` — `ui/src/core/probe.ts:10` — —
- `protocol.gen.ts` — `ui/src/core/protocol.gen.ts:1` — Автогенерация: `uv run python tools/gen_protocol.py`. Не редактировать.
- `Role` — `ui/src/core/store.svelte.ts:16` — —
- `MessageStatus` — `ui/src/core/store.svelte.ts:17` — —
- `TurnPhase` — `ui/src/core/store.svelte.ts:19` — Фаза хода для аватара и кнопки «Стоп»: ждём первый токен / идёт ответ / ничего.
- `ChatMessage` — `ui/src/core/store.svelte.ts:21` — —
- `SPAN_HISTORY` — `ui/src/core/store.svelte.ts:31` — Сколько последних замеров стадии хранить: хватает на p95, память — копейки.
- `AppStore` — `ui/src/core/store.svelte.ts:33` — —
- `CLOSE_REPLACED` — `ui/src/core/transport.ts:10` — Код закрытия «вытеснен новым клиентом» — `gateway/server.py` (ADR-0008).
- `SocketLike` — `ui/src/core/transport.ts:14` — Часть WebSocket, нужная транспорту: в тестах подменяется фейком.
- `SocketFactory` — `ui/src/core/transport.ts:24` — —
- `ConnectionState` — `ui/src/core/transport.ts:27` — `replaced` — ядро приняло другое окно; переподключаться нельзя, иначе окна вытесняют друг друга.
- `TransportListener` — `ui/src/core/transport.ts:29` — —
- `Backoff` — `ui/src/core/transport.ts:37` — Пауза перед попыткой n (с нуля): `min(maxMs, initialMs · factor^n)`.
- `TransportOptions` — `ui/src/core/transport.ts:43` — —
- `Transport` — `ui/src/core/transport.ts:66` — —

## ui/src/features/avatar
Публичный API фичи аватара: сцена и контракт рендера (ADR-0011).

- `AvatarSource` — `ui/src/features/avatar/AvatarRenderer.ts:13` — Что загрузить: файлы модели в `ui/public/avatars/<имя>/` (ADR-0011).
- `AvatarReaction` — `ui/src/features/avatar/AvatarRenderer.ts:24` — Реакция на ход разговора, не зависящая от текста: «слушаю» (пользователь печатает),
- `StageSize` — `ui/src/features/avatar/AvatarRenderer.ts:27` — Размер области сцены в CSS-пикселях; рендер сам учитывает devicePixelRatio.
- `AvatarRenderer` — `ui/src/features/avatar/AvatarRenderer.ts:32` — —
- `AvatarStage.svelte` — `ui/src/features/avatar/AvatarStage.svelte:1` — Сцена с аватаром: холст Live2D на всю панель, статус загрузки или ошибки поверх. Логика —
- `MAX_DELTA_MS` — `ui/src/features/avatar/loop.ts:7` — Шаг после паузы или подвисания ограничен: иначе физика волос «выстрелит» за один кадр.
- `FrameSource` — `ui/src/features/avatar/loop.ts:10` — Источник кадров: в окне — `requestAnimationFrame`, в тестах — ручной.
- `Visibility` — `ui/src/features/avatar/loop.ts:16` — Видимость окна: `onChange` возвращает функцию отписки.
- `browserFrames` — `ui/src/features/avatar/loop.ts:21` — —
- `browserVisibility` — `ui/src/features/avatar/loop.ts:28` — —
- `AvatarLoop` — `ui/src/features/avatar/loop.ts:38` — —
- `avatarSource` — `ui/src/features/avatar/session.ts:10` — Файлы модели `<имя>` в `ui/public/avatars/<имя>/` (ADR-0011).
- `AvatarStatus` — `ui/src/features/avatar/session.ts:18` — —
- `RendererFactory` — `ui/src/features/avatar/session.ts:22` — Создатель рендера: Live2D в окне, фейк в тестах.
- `AvatarSession` — `ui/src/features/avatar/session.ts:28` — —

## ui/src/features/avatar/live2d
—

- `CUBISM_CORE_URL` — `ui/src/features/avatar/live2d/core-loader.ts:8` — Где Vite отдаёт Core из `ui/public/live2d/`.
- `CORE_MISSING_MESSAGE` — `ui/src/features/avatar/live2d/core-loader.ts:10` — —
- `MAX_CORE_MAJOR` — `ui/src/features/avatar/live2d/core-loader.ts:18` — Старший номер Core, с которым работает движок: Core 6 (SDK 5-r.5) убрал
- `formatCoreVersion` — `ui/src/features/avatar/live2d/core-loader.ts:21` — Версия Core из `csmGetVersion()`: 0xMMmmpppp.
- `unsupportedCoreMessage` — `ui/src/features/avatar/live2d/core-loader.ts:25` — —
- `ScriptHost` — `ui/src/features/avatar/live2d/core-loader.ts:33` — Части `window`/`document`, нужные загрузчику: в тестах — подмена.
- `browserHost` — `ui/src/features/avatar/live2d/core-loader.ts:55` — —
- `loadCubismCore` — `ui/src/features/avatar/live2d/core-loader.ts:82` — Подключить Core один раз на окно; повторные вызовы ждут ту же загрузку.
- `Size` — `ui/src/features/avatar/live2d/fit.ts:3` — —
- `Placement` — `ui/src/features/avatar/live2d/fit.ts:8` — —
- `FIT_MARGIN` — `ui/src/features/avatar/live2d/fit.ts:16` — Поля вокруг модели, доля сцены: не упираться в края при наклонах головы и физике волос.
- `fitModel` — `ui/src/features/avatar/live2d/fit.ts:19` — Масштаб «вписать целиком» с полями; модель по центру. Пустая сцена или модель — масштаб 0.
- `gazeAt` — `ui/src/features/avatar/live2d/fit.ts:35` — Курсор → взгляд: -1…1 по осям, y вверх (как `AvatarRenderer.lookAt`). За пределами сцены
- `Live2DRenderer` — `ui/src/features/avatar/live2d/Live2DRenderer.ts:49` — —

## ui/src/features/chat
Публичный API фичи чата: приложение монтирует только панель (R-63).

- `Chat.svelte` — `ui/src/features/chat/Chat.svelte:1` — Панель чата: история, индикатор «печатает», ошибка ядра, поле ввода. Состояние — только из
- `Composer.svelte` — `ui/src/features/chat/Composer.svelte:1` — Поле ввода: Enter — отправить, Shift+Enter — перенос, Esc или «Стоп» — прервать ответ.
- `isSendKey` — `ui/src/features/chat/keys.ts:6` — Enter во время набора через IME (выбор иероглифа и т. п.) подтверждает ввод, а не отправляет.
- `isStopKey` — `ui/src/features/chat/keys.ts:10` — —
- `ESTIMATED_HEIGHT` — `ui/src/features/chat/layout.ts:8` — Оценка высоты не измеренного сообщения, px: реплика в 2–3 строки с отступами.
- `OVERSCAN_PX` — `ui/src/features/chat/layout.ts:10` — Запас над и под экраном, px: быстрая прокрутка не показывает пустоту до догрузки.
- `STICK_TOLERANCE_PX` — `ui/src/features/chat/layout.ts:12` — Насколько можно не докрутить до низа, чтобы список всё ещё «прилипал» к новым сообщениям.
- `Viewport` — `ui/src/features/chat/layout.ts:14` — —
- `Placed` — `ui/src/features/chat/layout.ts:19` — —
- `ListWindow` — `ui/src/features/chat/layout.ts:24` — —
- `computeWindow` — `ui/src/features/chat/layout.ts:56` — —
- `isAtBottom` — `ui/src/features/chat/layout.ts:76` — Пользователь внизу списка — новые сообщения прокручивают к себе; ушёл читать выше — нет.
- `MeasureTarget` — `ui/src/features/chat/measure.ts:7` — —
- `measureHeight` — `ui/src/features/chat/measure.ts:27` — —
- `MessageList.svelte` — `ui/src/features/chat/MessageList.svelte:1` — Виртуализированная история: в DOM только окно вокруг экрана (layout.ts), строки

## ui/src/features/metrics
Публичный API фичи метрик: панель и её горячая клавиша (R-63).

- `METRICS_HOTKEY_LABEL` — `ui/src/features/metrics/hotkey.ts:5` — Горячая клавиша панели метрик (FR-15): Ctrl+Shift+M. F12 занят инструментами разработчика
- `isMetricsHotkey` — `ui/src/features/metrics/hotkey.ts:10` — По `code`, а не `key`: в русской раскладке `key` для этой клавиши — «Ь».
- `MetricsPanel.svelte` — `ui/src/features/metrics/MetricsPanel.svelte:1` — Панель метрик для разработчика (FR-15): задержки стадий хода — от ядра (`metrics.span`) и
- `Summary` — `ui/src/features/metrics/stats.ts:7` — —
- `percentile` — `ui/src/features/metrics/stats.ts:27` — Перцентиль по ближайшему рангу: значение из выборки, без интерполяции — честно для малых n.
- `summarize` — `ui/src/features/metrics/stats.ts:35` — —
- `summarizeAll` — `ui/src/features/metrics/stats.ts:48` — Строки панели: сначала стадии с бюджетом (главное), затем остальные по имени.
- `overBudget` — `ui/src/features/metrics/stats.ts:57` — —
