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

## Зависимости
- application: `ConversationService`; domain: события, `Emotion`; kernel: `EventBus`

## События
- Публикует: —
- Слушает: `TurnFinished` (печать TTFT), `TurnCancelled` (причина или текст ошибки)

## Инварианты (тесты `tests/unit/gateway/test_terminal.py`)
- Новая строка во время ответа прерывает его (`NEW_MESSAGE`), `/stop` — `USER_STOP`.
- Конец ввода — дождаться текущего ответа; `/exit` — прервать и выйти.
- TTFT = первая показанная порция (текст или эмоция) − момент отправки реплики.

## Производительность
- Запись в консоль синхронная — несколько байт на порцию, инструмент разработчика.

## Как расширять
- Этап 4: `protocol.py`, `codec.py`, `sink.py` (`WsReplySink`), `server.py`.

## Связанные документы
`docs/architecture.md` (Протокол UI ↔ Ядро), STAGE_03 (веха M1), STAGE_04
