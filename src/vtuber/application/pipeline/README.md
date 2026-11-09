# application/pipeline — конвейер ответа: LLM → разбор тегов → нарезка фраз → TTS

## Ответственность
Превращает поток дельт LLM в то, что нужно потребителям: текст для чата, текст для озвучки,
события эмоций, текст для истории — и стримит это получателю (`ReplySink`) по мере генерации.
Две ветки: текстовая (`StreamParser` → `sink.text/emotion`) и, с голосом, TTS-ветка
(`SentenceChunker` → очередь фраз → `Speaker`: нормализация → `TTSPort` → `sink.audio`), которая
работает параллельно с генерацией (T-02); звук ответа опаздывает — междометие из `FillerBank`
(T-17). НЕ строит промпт, не хранит историю, не решает судьбу прерванного хода
(ConversationService, S-3.5), не нормализует числа для TTS (`application/speech`), не знает о
WebSocket.

## Публичный API (`__init__.py`)
| Символ | Назначение |
|---|---|
| `PhraseListener`, `Voice.on_phrase` | Сообщение `PhraseVoiced` об озвученной фразе: когда зазвучит и сколько продлится (субтитры) |
| `ReplyPipeline(llm, params, telemetry, voice=None)` | `run(messages, sink, parser)` — стрим ответа в `sink`; с `Voice` — и звук |
| `Voice(tts, chunker, fillers=None)` | Голос хода: движок, правила нарезки, междометия; нет — только текст |
| `Speaker(tts, telemetry, fillers=None)` | TTS-ветка: `run(phrases, sink)` до маркера `None` |
| `FillerBank(cfg)` | Междометия: `prepare(tts)` — синтез один раз, `ready`, `after_s`, `next_clip()` по кругу |
| `FillerConfig` | `[pipeline.filler]`: `enabled`, `after_ms`, `phrases` |
| `AudioOut(sink)` | Единственный писатель звука хода: `answer(chunk)`, `filler(clip) → bool` |
| `PipelineConfig` | Секция `[pipeline]`: `chunker`, `filler` |
| `StreamParser` | `feed(delta) → [ParseEvent]`, `flush() → [ParseEvent]`, `full_text` |
| `TextDelta` | `text` (чат) и `spoken_text` (TTS: без эмодзи и разметки); `deliver(sink)` |
| `EmotionCue` | Известный тег эмоции; `spoken_text == ""`; `deliver(sink)` |
| `ParseEvent` | `TextDelta \| EmotionCue` |
| `SentenceChunker(cfg)` | `feed(text) → Iterator[фраза]`, `flush() → хвост \| None`; один на ход (T-02) |
| `ChunkerConfig` | `[pipeline.chunker]`: `first_min_words`, `next_min_words`, `max_words` |
| `HOLD_LIMIT` | Максимум символов незакрытого «<», которые придерживаются (32) |
| `Delivery(fillers, on_phrase, normalize)`, `Voice.diction` | Что кроме движка нужно речи хода; дикция издания — нормализатор и сокращения нарезки (Этап 20); `SentenceChunker(cfg, abbreviations)`, `FillerBank(cfg, normalize)` |

## Зависимости
- Порты: `LLMPort`, `GenerationParams`, `ReplySink`, `TTSPort`; `application/speech` (нормализация)
- domain: `Emotion`, `Message`, `parse_tag`, `TAG_OPEN`, `TAG_CLOSE`; kernel: `Telemetry`

## События
- Публикует: — (метрики `llm.first_token`, `llm.stream`, `tts.first_audio`, `tts.phrase` — через
  `Telemetry`)
- Слушает: —

## Инварианты
- Разбор (`test_stream_parser.py`): склейка `text` == вход без тегов при любом разбиении
  (property); `EmotionCue` — известные теги по порядку; «<» не в форме `<слово>` — текст;
  недописанный известный тег в конце выбрасывается; текст без «<» отдаётся сразу (T-01).
- Конвейер (`test_reply_pipeline.py`): текст доходит до `sink` до конца генерации; `done` —
  только при полном ответе; отмена и ошибка закрывают поток LLM (`aclosing`) и пролетают
  наружу; после отмены `parser.full_text` — показанная часть.
- Конвейер не ветвится по типам событий: каждое само себя доставляет (`deliver`).
- TTS-ветка (`test_reply_pipeline_voice.py`): первая фраза уходит в TTS раньше, чем LLM закончил;
  в TTS — нормализованный текст без тегов; `done` — после последнего звука; недоступный TTS
  молчит до конца хода, сбой фразы пропускает только её — текст доходит; отмена хода отменяет и
  синтез, `done` нет; `tts.first_audio` — один раз и только если звук был.
- Междометия (`test_filler.py`): звучат, только если к `after_ms` звука ответа нет; ответ,
  пришедший во время междометия, ждёт его конца — фрагменты не перемешиваются; начавшийся
  ответ отменяет междометие; ход, кончившийся до срока, междометия не получает. В
  `tts.first_audio` междометие не в счёт (в `ui.first_audio` UI — в счёт: это слышимый звук).
- Нарезка (`test_chunker.py`): результат не зависит от разбиения потока на дельты, склейка
  фраз == вход с точностью до пробелов (property); первая фраза — по запятой после
  `first_min_words`, дальше — после `next_min_words`; `.!?…` и перенос строки режут всегда;
  `3.5`, `т.е.`, инициалы не режутся; закрывающие кавычки и скобки остаются во фразе; без
  знаков — разрез по пробелу после `max_words`. Разрез — только когда виден символ после знака.

## Производительность
- TTS-ветка — отдельная задача: синтез фразы N идёт, пока LLM пишет N+1 (T-02); очередь фраз без
  ограничения (фраз в ходе — единицы). TTFA ядра (`tts.first_audio`, FakeLLM ~50 ток/с,
  машина разработки): Silero p50 231 мс, Piper p50 237 мс.
- Горячий путь: да. `feed` — O(дельта + хвост ≤ 32), одна регулярка на порцию; доставка —
  прямой `await` без шины (T-15); два `span` ≈ 3 мкс на ход.

## Как расширять
- Новая эмоция — только в `domain.Emotion`.
- Другие междометия или срок — `[pipeline.filler]` в конфиге, без кода.

## Связанные документы
`docs/architecture.md` (Конвейер ответа, Разбор эмоций), T-01, T-14, T-15; карточка `ports`
