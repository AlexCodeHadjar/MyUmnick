# adapters/llm — адаптеры языковых моделей (LLMPort)

## Ответственность
Реализации `LLMPort` для конкретных серверов. Переводят доменные сообщения в HTTP-запросы,
разбирают стрим ответа, переводят исключения httpx в доменные (R-43). НЕ строят промпт, не
знают о персоне, истории и UI; не импортируют application, gateway и другие адаптеры.

## Публичный API (`__init__.py`)
| Символ | Назначение |
|---|---|
| `LlamaServerProcess(cfg, base_url)`, `LlamaServerConfig`, `server_arguments` | llama-server как дочерний процесс (ADR-0019): `async with`, `wait_ready()`, `healthy()`, `restart()`; привязан к ядру через Job Object (`ChildBinding`, ADR-0021); выключен — ничего не делает |
| `LLMConfig` | Секция `[llm]`: `backend`, `base_url`, `model`, тайм-ауты, `llamacpp`, `generation` |
| `GenerationConfig` | `[llm.generation]`: `max_tokens`, `temperature` (T-07) |
| `LlamaCppOptions` | `[llm.llamacpp]`: `slot_id` (слот диалога), `enable_thinking` |
| `OpenAICompatLLM` | `/v1/chat/completions` со стримом SSE; `async with` владеет httpx-клиентом |
| `LlamaCppLLM` | Наследник: слот, `cache_prompt`, `chat_template_kwargs`, настоящий `prefill` |

Внутренние модули: `sse.py` (разбор строк SSE); в `openai_compat.py` — `wire_messages`,
`check_status`, `UNREACHABLE` для наследников.
| `NO_FOREIGN_OR_CYRILLIC_GRAMMAR`, `[llm.llamacpp].forbid_cyrillic` | Английское издание: ответ без кириллицы (Этап 20) |

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
- `data: [DONE]` завершает стрим; порции без текста пропускаются; `stop` — только если задан.
- Отмена потребителя закрывает соединение: сервер видит обрыв (T-14).
- `OpenAICompatLLM.prefill` — только проверка `/v1/models`.
- `LlamaCppLLM`: каждый запрос чата — `id_slot`, `cache_prompt: true`,
  `chat_template_kwargs.enable_thinking`; `prefill` = `/apply-template` (промпт шаблоном модели —
  совпадает с тем, что отрендерит чат) → `/completion` с `n_predict: 0` в слот диалога.

## Производительность
- Горячий путь: да. Соединение переиспользуется пулом между ходами; разбор порции — один
  `json.loads`. KV-кэш слота диалога переиспользуется (T-03); `prefill` прогревает его заранее
  (T-05 при наборе — Этап 9, T-06 при старте — bootstrap, S-3.5). Замеры TTFT — S-2.4.

## Проверено / не проверено
- Заглушка `tests/llm_stub.py` и MockTransport — все ветки, контракт LLM для обоих адаптеров.
- Против настоящего llama-server — тесты `@gpu` (`tests/integration/test_llamacpp.py`: ответ без
  `<think>`, освобождение слота после отмены). Запуск на целевой машине:
  `scripts/start_llm.ps1 -Model …`, затем `uv run pytest -m gpu`. Пока не выполнялись.
- Принимает ли `/v1/chat/completions` поля `id_slot` и `chat_template_kwargs` — по README не
  подтверждено (описаны для `/completion`); reasoning выключен ещё и флагом сервера.

## Как расширять
- Новый сервер: модуль рядом, вход в `http_adapters` в `tests/contract/factories.py`.
- Выбор адаптера по `[llm].backend` — реестр `bootstrap.llm_backends()`; новый адаптер — строка там.

## Связанные документы
ADR-0002, ADR-0007, `docs/architecture.md`, T-01, T-03, T-05, T-06, T-08, T-14, R-36, R-43
