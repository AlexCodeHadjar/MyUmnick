# adapters/llm — адаптеры языковых моделей (LLMPort)

## Ответственность
Реализации `LLMPort` для конкретных серверов. Переводят доменные сообщения в HTTP-запросы,
разбирают стрим ответа, переводят исключения httpx в доменные (R-43). НЕ строят промпт, не
знают о персоне, истории и UI; не импортируют application, gateway и другие адаптеры.

## Публичный API (`__init__.py`)
| Символ | Назначение |
|---|---|
| `LLMConfig` | Секция `[llm]`: `base_url`, `model`, `connect_timeout_s`, `read_timeout_s` |
| `OpenAICompatLLM` | `/v1/chat/completions` со стримом SSE; `async with` владеет httpx-клиентом |

Внутренние модули: `sse.py` (`data_of`, `delta_text`, `SSE_DONE`) — разбор строк SSE.

## Зависимости
- Порты: `LLMPort`, `GenerationParams`; domain: `Message`, `LLMUnavailable`, `GenerationFailed`
- Kernel: `ConfigSection`
- Внешние: httpx (ADR-0007)

## События
- Публикует: —
- Слушает: —

## Инварианты
- Один `httpx.AsyncClient` на адаптер, `trust_env=False`; закрывается при выходе из `async with`.
- Нет соединения / тайм-аут соединения / 503 (модель грузится) → `LLMUnavailable` с подсказкой.
- Иной HTTP-код, обрыв посреди стрима, мусор в порции → `GenerationFailed` (текст ответа
  сервера — в сообщении, до 300 символов).
- `data: [DONE]` завершает стрим; порции без текста (роль, пустые `choices`) пропускаются.
- `stop` в теле запроса — только если задан.
- Отмена потребителя закрывает соединение: сервер видит обрыв (T-14) —
  `tests/integration/test_openai_compat.py`.
- `prefill` общего API — только проверка `/v1/models` (прогрева кэша здесь нет).

## Производительность
- Горячий путь: да. Соединение переиспользуется пулом между ходами; разбор порции — один
  `json.loads`. Замеры TTFT — S-2.4.

## Как расширять
- Новый сервер: модуль рядом, `LLMCase` в `tests/contract/factories.py` (рабочий и недоступный).
- llama.cpp (S-2.3): поверх того же клиента — `id_slot`, `cache_prompt`, настоящий `prefill`.
- Выбор адаптера по конфигу (`Registry`, поле `backend`) — при сборке в bootstrap (S-3.5).

## Связанные документы
ADR-0002, ADR-0007, `docs/architecture.md` (Процессы, Ошибки), T-01, T-14, R-36, R-43
