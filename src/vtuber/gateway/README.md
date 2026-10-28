# gateway — интерфейсы к ядру: протокол, WebSocket-сервер для UI, терминальный чат

## Ответственность
Переводит внешний ввод в вызовы `ConversationService` и выводит результат: сейчас — терминальный
чат для вехи M1 и WebSocket-сервер для UI (протокол v1, `WsReplySink`). НЕ создаёт адаптеры
и не знает о них (контракт слоёв), не строит промпт.

## Публичный API (`__init__.py`)
| Символ | Назначение |
|---|---|
| `TerminalChat(service, bus, read_line, out)` | `run()` — цикл чата до `/exit` или конца ввода |
| `TerminalSink(out, started_ns)` | `ReplySink` для консоли: печать по мере генерации, время первой порции |
| `EXIT_COMMAND`, `STOP_COMMAND` | `/exit` — выход, `/stop` — прервать ответ |
| `PROTOCOL_VERSION`, `turn_ref` | Версия протокола (1); номер хода в JSON — `t-000042` |
| `ChatSend`, `ChatCancel`, `InboundMessage` | UI → Ядро (дискриминатор `type`) |
| `TurnStartedMessage`, `ChatDelta`, `AvatarEmotion`, `TurnFinishedMessage`, `TurnCancelledMessage`, `MetricsSpan`, `Status`, `ErrorMessage`, `OutboundMessage` | Ядро → UI; `.of(...)` — короткие конструкторы |
| `ErrorCode` и `*Data` | Коды ошибок и полезная нагрузка сообщений |
| `decode_inbound`, `encode_outbound` | JSON ↔ модели; битое сообщение → `ProtocolError` |
| `encode_audio_frame`, `decode_audio_frame`, `AudioFrame` | Бинарный аудиокадр: 16 байт заголовка + PCM |
| `GatewayServer(service, bus, cfg)`, `GatewayConfig` | WebSocket-сервер: `async with`, `serve_forever()`, `send()`, `port`; `[gateway]` host/port |
| `WsReplySink(send, send_bytes)` | Ответ хода → `chat.delta` / `avatar.emotion` / бинарный аудиокадр (`seq` с нуля в каждом ходе); ход — из `kernel.current_turn()` |
| `REPLACED_CODE` | 4000 — код закрытия вытесненного клиента |

## Зависимости
- application: `ConversationService`; domain: события, `Emotion`; kernel: `EventBus`

## События
- Публикует: —
- Терминал слушает: `TurnFinished` (печать TTFT), `TurnCancelled` (причина или текст ошибки).
- Сервер слушает: `TurnStarted`, `TurnFinished`, `TurnCancelled`, `MetricRecorded`,
  `BackendStatusChanged` → соответствующие сообщения клиенту; последний статус бэкенда
  отправляется при подключении.

## Инварианты
- Протокол (`test_protocol.py`): каждое сообщение Ядро → UI проходит круг JSON ↔ модель;
  конверт `{"v":1,"type":…,"turn":…,"data":{…}}`; от UI — строгая проверка (лишнее поле, пустой
  текст, другая версия, неизвестный тип → `ProtocolError`); аудиокадр — по таблице смещений
  `docs/architecture.md`, `seq` по модулю 2^16.
- Протокол меняется только в `protocol.py`; `ui/src/core/protocol.gen.ts` и `docs/protocol.md`
  генерирует `tools/gen_protocol.py` (хук и CI роняют сборку, если файлы устарели).
- Сервер (`tests/integration/test_ws_server.py`): ход по сокету `turn.started → chat.delta… →
  turn.finished`; битое или бинарное сообщение → `error bad_message`, соединение живёт;
  `chat.cancel` останавливает ход; новый клиент вытесняет старого (4000); отключение посреди
  хода отменяет его (T-14); дельта LLM → кадр у клиента ≤ 3 мс p95.
- Терминал (`test_terminal.py`): новая строка во время ответа прерывает его (`NEW_MESSAGE`),
  `/stop` — `USER_STOP`.
- Конец ввода — дождаться текущего ответа; `/exit` — прервать и выйти.
- TTFT = первая показанная порция (текст или эмоция) − момент отправки реплики.

## Производительность
- Запись в консоль синхронная — несколько байт на порцию, инструмент разработчика.
- JSON — pydantic-core (нативный код), без orjson; аудио — `struct` + одна склейка с PCM.

## Как расширять
- Новое сообщение — модель в `protocol.py` и вход в `InboundMessage`/`OutboundMessage`, вместе с
  кодом, который его использует (`input.typing` — Этап 9, `audio.played`, `settings.*` — Этап 7+,
  `mic.frame` — Этап 11).
- Микрофон (Этап 11): бинарные кадры от UI → `mic.frame` вместо `bad_message`.

## Связанные документы
`docs/architecture.md` (Протокол UI ↔ Ядро), STAGE_03 (веха M1), STAGE_04
