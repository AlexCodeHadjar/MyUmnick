# application/memory — память витюбера: история, её резюме, долговременные факты

## Ответственность
Хранит ходы текущего разговора и отдаёт их промпту, усекая историю редко и сразу блоком (T-04).
В простое (T-13) — через планировщик и отдельный слот LLM — сжимает отрезанное в резюме и
извлекает из ходов факты о пользователе в долговременную память (FR-10). В ходе — гейт поиска
(T-12) и справка из найденных фактов. Не держит модели и базы (это адаптеры за портами), не
решает судьбу прерванного хода (ConversationService).

## Публичный API (`__init__.py`)
| Символ | Назначение |
|---|---|
| `MemoryEditor(vault, store, embedder)`, `MemoryControls` | Правка и удаление фактов из UI; индекс сверяется сразу (S-16.2) |
| `MemoryEraser(vault, store, history, quiet)` | Очистка всей памяти (S-17.2): сначала останавливает запись, потом удаляет |
| `VaultedFacts(store, vault)`, `reconcile(vault, store, embedder)`, `VaultWatcher(vault, submit, sync, poll_s)`, `ChatRecorder(vault)` | Заметки — источник истины, индекс — производная (ADR-0020): запись факта, сверка, импорт, слежение за правками, запись чатов своей задачей |
| `without_viewer_turns(messages)` | Реплики зрителей не идут в резюме (FR-31) |
| `ShortTermMemory(budget)` | `append(turn) → отрезанные сообщения`; `messages` (резюме — в первой реплике); `tokens`; `summary`, `set_summary` |
| `INTERRUPTED_MARK`, `SUMMARY_TEMPLATE` | «…» на конце прерванного ответа; как резюме встраивается в первую реплику |
| `Summarizer(llm, params)` | `summarize(previous, dropped) → str` — новое резюме вбирает прежнее, ≤ `MAX_SUMMARY_CHARS` |
| `FactExtractor(llm, params)`, `parse_facts(raw)`, `ExtractedFact` | Ход → факты строгим JSON; не JSON или не по схеме — `GenerationFailed` |
| `FactMemory(extractor, embedder, store, cfg)`, `FactMemoryConfig` | `learn(turn, when) → записано`: извлечь, отсеять повторы (`dedup_score`), запомнить с вектором |
| `needs_memory(text)`, `is_factual_question(text)` | Гейт поиска (T-12): эвристики без модели |
| `MemoryRecall(embedder, store, cfg, telemetry)`, `RetrievalConfig`, `TurnHints` | `hints(text)` — справка из фактов и температура на ход; сбой или тайм-аут памяти ход не задерживают |
| `MemoryKeeper(scheduler, history, summarizer, facts)` | `follow(bus)`: по `TurnRemembered` — задачи простоя «резюме» (если отрезано) и «факты» |

## Зависимости
- application: `prompting.ContextBudget`, `scheduler.IdleScheduler`/`IdleJob`
- Порты: `LLMPort`, `EmbedderPort`, `MemoryStorePort`, `GenerationParams`
- domain: `Turn`, `Message`, `Fact`, `TurnRemembered`, ошибки; kernel: `EventBus`, `ConfigSection`

## События
- Публикует: —
- Слушает: `TurnRemembered` (через `MemoryKeeper.follow`) — публикует ConversationService после
  записи хода в историю.

## Инварианты
- История (`test_short_term.py`, property): чередование user/assistant; только дописывание в
  бюджете; превышение — отрезаются старшие целые ходы до `trim_target`; новый ход не режется;
  прерванный ответ — с «…».
- Резюме (`test_summarizer_and_history.py`): в первой реплике истории (не отдельный system —
  не все шаблоны чата его допускают), чередование сохраняется; вбирает прежнее; обрезается по
  предложению; пустое — `GenerationFailed`. Без истории резюме не выводится.
- Факты (`test_fact_extractor.py` — ответы в обёртке ```json, с пояснениями, лишними полями;
  кривые — `GenerationFailed`; `test_facts_and_keeper.py`): повторы внутри ответа — по тексту,
  с памятью — по смыслу (близость ≥ `dedup_score`, 0.97: новые факты важнее дублей); источник `extracted`, время — с поясом;
  перезапуск задачи факт не дублирует.
- Поиск (`test_retrieval_gate.py`): гейт закрыт — эмбеддер не вызывается (0 мс); открыт — факты
  с близостью ≥ `min_score` идут в `context` реплики; в истории реплика остаётся чистой. Вопрос о
  мире без найденных фактов — `factual_temperature`.
- Фон (`test_facts_and_keeper.py`): задачи — только через планировщик простоя; кривой JSON
  роняет лишь свою задачу — резюме и очередь живут; ход не ждёт память.

## Производительность
- Горячий путь: только `ShortTermMemory` — `append` O(1), усечение раз в много ходов. Резюме и
  факты — вне хода, в простое, в слоте LLM 1 (кэш диалога в слоте 0 не трогается).

## Как расширять
- Другие фоновые задачи памяти — ещё одна `IdleJob` в `MemoryKeeper.on_turn`.
- Записанные ответы настоящей модели — добавить в `test_fact_extractor.py` на целевой машине.

## Связанные документы
`docs/performance.md` (T-03, T-04, T-13), ADR-0015, карточки `application/prompting`,
`application/scheduler`, `adapters/memory`
