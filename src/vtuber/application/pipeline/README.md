# application/pipeline — конвейер ответа: LLM → разбор тегов → нарезка фраз → TTS

## Ответственность
Превращает поток дельт LLM в то, что нужно потребителям: текст для чата, текст для озвучки,
события эмоций, текст для истории — и стримит это получателю (`ReplySink`) по мере генерации.
Сейчас — текстовая ветка: `StreamParser` и `ReplyPipeline`, и `SentenceChunker` для будущей
TTS-ветки (S-7.5). НЕ строит промпт, не хранит историю, не решает судьбу прерванного хода
(ConversationService, S-3.5), не нормализует числа для TTS (`application/speech`), не знает о
WebSocket.

## Публичный API (`__init__.py`)
| Символ | Назначение |
|---|---|
| `ReplyPipeline(llm, params, telemetry)` | `run(messages, sink, parser)` — стрим ответа в `sink` |
| `StreamParser` | `feed(delta) → [ParseEvent]`, `flush() → [ParseEvent]`, `full_text` |
| `TextDelta` | `text` (чат) и `spoken_text` (TTS: без эмодзи и разметки); `deliver(sink)` |
| `EmotionCue` | Известный тег эмоции; `spoken_text == ""`; `deliver(sink)` |
| `ParseEvent` | `TextDelta \| EmotionCue` |
| `SentenceChunker(cfg)` | `feed(text) → Iterator[фраза]`, `flush() → хвост \| None`; один на ход (T-02) |
| `ChunkerConfig` | Секция `[pipeline.chunker]`: `first_min_words`, `next_min_words`, `max_words` (в `default.toml` — с S-7.5) |
| `HOLD_LIMIT` | Максимум символов незакрытого «<», которые придерживаются (32) |

## Зависимости
- Порты: `LLMPort`, `GenerationParams`, `ReplySink`
- domain: `Emotion`, `Message`, `parse_tag`, `TAG_OPEN`, `TAG_CLOSE`; kernel: `Telemetry`

## События
- Публикует: — (метрики `llm.first_token`, `llm.stream` — через `Telemetry`)
- Слушает: —

## Инварианты
- Разбор (`test_stream_parser.py`): склейка `text` == вход без тегов при любом разбиении
  (property); `EmotionCue` — известные теги по порядку; «<» не в форме `<слово>` — текст;
  недописанный известный тег в конце выбрасывается; текст без «<» отдаётся сразу (T-01).
- Конвейер (`test_reply_pipeline.py`): текст доходит до `sink` до конца генерации; `done` —
  только при полном ответе; отмена и ошибка закрывают поток LLM (`aclosing`) и пролетают
  наружу; после отмены `parser.full_text` — показанная часть.
- Конвейер не ветвится по типам событий: каждое само себя доставляет (`deliver`).
- Нарезка (`test_chunker.py`): результат не зависит от разбиения потока на дельты, склейка
  фраз == вход с точностью до пробелов (property); первая фраза — по запятой после
  `first_min_words`, дальше — после `next_min_words`; `.!?…` и перенос строки режут всегда;
  `3.5`, `т.е.`, инициалы не режутся; закрывающие кавычки и скобки остаются во фразе; без
  знаков — разрез по пробелу после `max_words`. Разрез — только когда виден символ после знака.

## Производительность
- Горячий путь: да. `feed` — O(дельта + хвост ≤ 32), одна регулярка на порцию; доставка —
  прямой `await` без шины (T-15); два `span` ≈ 3 мкс на ход.

## Как расширять
- TTS-ветка (S-7.5): `spoken_text` → `SentenceChunker` → очередь фраз → `TTSPort`, параллельно
  с генерацией (`TaskGroup`); `ReplySink.audio`.
- Новая эмоция — только в `domain.Emotion`.

## Связанные документы
`docs/architecture.md` (Конвейер ответа, Разбор эмоций), T-01, T-14, T-15; карточка `ports`
