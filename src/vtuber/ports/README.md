# ports — Protocol-интерфейсы ядра к внешнему миру

## Ответственность
Что ядру нужно от бэкендов — в терминах домена. Только `typing.Protocol` и значения-параметры.
НЕ содержит реализаций (это adapters), не знает о httpx/torch/websockets, не импортирует kernel.
Каждый порт закреплён контрактным тестом, который проходят все его адаптеры (R-57, LSP).

## Публичный API (`__init__.py`)
| Символ | Назначение |
|---|---|
| `LLMPort` | `stream(messages, params)` → `AsyncGenerator[str]` (закрывать через `aclosing`); `prefill(messages)` |
| `GenerationParams` | `max_tokens`, `temperature`, `stop`; значения — из конфига |
| `ReplySink` | Получатель хода: `text(delta)`, `emotion(e)`, `done()` (`done` — только при полном ответе); `audio` — S-7.5 |

## Зависимости
- Только domain (`Message`, доменные ошибки).

## События
- Публикует: —
- Слушает: —

## Инварианты (контракт `tests/contract/test_llm_contract.py`)
- `stream` отдаёт непустой текст строками.
- Отмена потребителя завершает его ≤ 50 мс и пролетает `CancelledError`; адаптер при этом
  закрывает поток генерации (T-14) — для реального сервера проверяет интеграционный тест.
- Недоступный бэкенд: `stream` и `prefill` бросают `LLMUnavailable`, а не чужое исключение.
- Сбой посреди ответа — `GenerationFailed`.

## Как расширять
- Новый адаптер LLM: класс в `adapters/llm/`, `LLMCase` в `tests/contract/factories.py`
  (рабочий и недоступный вариант) — контракт прогонится автоматически.
- Новый порт: Protocol + фейк в `tests/fakes/` + контрактный тест (порядок из WORKFLOW).
- Дальше появятся: `TTSPort` (S-7.1), `STTPort` (S-11.2), порты памяти
  (S-10.1).

## Связанные документы
ADR-0001, `docs/architecture.md` (Порты), `docs/testing.md` (Контрактные тесты), T-01, T-05, T-14
