# gateway — интерфейсы к ядру: терминальный чат (далее — WebSocket-сервер для UI)

## Ответственность
Переводит внешний ввод в вызовы `ConversationService` и выводит результат: сейчас — терминальный
чат для вехи M1; на Этапе 4 — WebSocket-сервер, протокол и `WsReplySink`. НЕ создаёт адаптеры
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

## Зависимости
- application: `ConversationService`; domain: события, `Emotion`; kernel: `EventBus`

## События
- Публикует: —
- Слушает: `TurnFinished` (печать TTFT), `TurnCancelled` (причина или текст ошибки)

## Инварианты
- Протокол (`test_protocol.py`): каждое сообщение Ядро → UI проходит круг JSON ↔ модель;
  конверт `{"v":1,"type":…,"turn":…,"data":{…}}`; от UI — строгая проверка (лишнее поле, пустой
  текст, другая версия, неизвестный тип → `ProtocolError`); аудиокадр — по таблице смещений
  `docs/architecture.md`, `seq` по модулю 2^16.
- Протокол меняется только в `protocol.py`; TS-типы и `docs/protocol.md` генерируются (S-4.3).
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
- S-4.2: `sink.py` (`WsReplySink`), `server.py`.

## Связанные документы
`docs/architecture.md` (Протокол UI ↔ Ядро), STAGE_03 (веха M1), STAGE_04
