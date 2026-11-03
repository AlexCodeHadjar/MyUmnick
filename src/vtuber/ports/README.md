# ports — Protocol-интерфейсы ядра к внешнему миру

## Ответственность
Что ядру нужно от бэкендов — в терминах домена. Только `typing.Protocol` и значения-параметры.
НЕ содержит реализаций (это adapters), не знает о httpx/torch/websockets, не импортирует kernel.
Каждый порт закреплён контрактным тестом, который проходят все его адаптеры (R-57, LSP).

## Публичный API (`__init__.py`)
| Символ | Назначение |
|---|---|
| `GpuProbe` | `memory()` → `GpuMemory` или None: фактическая занятость видеопамяти (ADR-0018) |
| `ManagedModel` | `load()`, `unload()`: модель под управлением менеджера ресурсов (ADR-0017) |
| `MessageSource` | `messages()` → `AsyncGenerator[IncomingMessage]`: реплики извне (чат стрима), сам восстанавливает соединение |
| `LLMPort` | `stream(messages, params)` → `AsyncGenerator[str]` (закрывать через `aclosing`); `prefill(messages)` |
| `GenerationParams` | `max_tokens`, `temperature`, `stop`; значения — из конфига |
| `TTSPort` | `audio_format` (частота PCM движка); `synthesize(phrase)` → `AsyncGenerator[AudioChunk]` (закрывать через `aclosing`) |
| `EmbedderPort` | `dimensions`; `embed(texts, kind)` → `list[Vector]` по порядку (`EmbedKind.QUERY`/`PASSAGE`) |
| `MemoryStorePort` | `add(fact, vector)` → `FactId`; `search(query, limit)` → `list[FactHit]` от самого близкого |
| `ReplySink` | Получатель хода: `text(delta)`, `emotion(e)`, `audio(chunk)`, `done()` (`done` — только при полном ответе, после последнего звука) |

## Зависимости
- Только domain (`Message`, доменные ошибки).

## События
- Публикует: —
- Слушает: —

## Инварианты LLMPort (контракт `tests/contract/test_llm_contract.py`)
- `stream` отдаёт непустой текст строками.
- Отмена потребителя завершает его ≤ 50 мс и пролетает `CancelledError`; адаптер при этом
  закрывает поток генерации (T-14) — для реального сервера проверяет интеграционный тест.
- Недоступный бэкенд: `stream` и `prefill` бросают `LLMUnavailable`, а не чужое исключение.
- Сбой посреди ответа — `GenerationFailed`.

## Инварианты TTSPort (контракт `tests/contract/test_tts_contract.py`)
- Все фрагменты — в `audio_format`, PCM s16 целыми сэмплами; пустая фраза — без звука и без
  ошибки.
- Отмена потребителя после первого фрагмента завершает его ≤ 50 мс и пролетает
  `CancelledError` (половина бюджета «отмена → тишина ≤ 100 мс» Этапа 7).
- Ранний выход через `aclosing` чист: следующий синтез работает.
- Недоступный движок — `TTSUnavailable`; сбой посреди фразы — `GenerationFailed`.

## Инварианты портов памяти (`test_embedder_contract.py`, `test_memory_store_contract.py`)
- Эмбеддер: вектор на каждый текст по порядку, размерности `dimensions`, единичной длины;
  пустой пакет — пустой ответ; тот же текст — тот же вектор в любом пакете; близкий по смыслу
  запрос ближе далёкого текста; нет модели — `MemoryUnavailable`.
- Хранилище: пустое — пустая выдача; факт находится своим вектором первым (близость ≈ 1) со
  всеми полями; выдача по убыванию близости, не длиннее `limit`; вектор не той размерности и
  `limit` < 1 — `ValueError`; не открыто — `MemoryUnavailable`.
- Порты раздельны (ISP): эмбеддер меняется с моделью, хранилище — с базой; гейту поиска нужен
  только эмбеддер.

## Как расширять
- Новый адаптер LLM: класс в `adapters/llm/`, `LLMCase` в `tests/contract/factories.py`
  (рабочий и недоступный вариант) — контракт прогонится автоматически.
- Новый адаптер TTS: класс в `adapters/tts/`, `TTSCase` в `tests/contract/factories.py`; нет
  модели на машине — случай пропускается с причиной, фейк проверяется всегда.
- Новый порт: Protocol + фейк в `tests/fakes/` + контрактный тест (порядок из WORKFLOW).
- Новый адаптер памяти: `EmbedderCase`/`StoreCase` в `tests/contract/memory_factories.py`.
- Голосовой ввод: `VadPort`, `STTPort` (`tests/contract/test_stt_contract.py`, ADR-0016).

## Связанные документы
ADR-0001, `docs/architecture.md` (Порты), `docs/testing.md` (Контрактные тесты), T-01, T-05, T-14
