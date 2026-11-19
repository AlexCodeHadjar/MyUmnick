# PROJECT MAP

> Автогенерация: `python -m tools.gen_map`. Не редактировать.

## src/vtuber
Ядро локального ИИ-витюбера.

## src/vtuber/adapters
Адаптеры: реализации портов для конкретных движков.

## src/vtuber/adapters/chats
Адаптер каталога чатов: JSON рядом с памятью издания (Этап 21, ADR-0037).

- `JsonChatCatalog` — `src/vtuber/adapters/chats/json_catalog.py:25` — Реализует `ChatCatalogPort`; файл пишется через временный — сбой не оставит битый каталог.

## src/vtuber/adapters/gpu
Опрос видеокарты для менеджера ресурсов (ADR-0018).

- `NvidiaSmiConfig` — `src/vtuber/adapters/gpu/nvidia_smi.py:22` — Подсекция опроса: срок одного вызова.
- `parse_memory` — `src/vtuber/adapters/gpu/nvidia_smi.py:28` — Первая видеокарта из вывода `nvidia-smi`; непонятный вывод — None.
- `NvidiaSmiProbe` — `src/vtuber/adapters/gpu/nvidia_smi.py:37` — `GpuProbe`: None, если утилиты нет, карта не NVIDIA или вызов не уложился в срок.

## src/vtuber/adapters/llm
Адаптеры языковых моделей (LLMPort).

- `LlamaCppOptions` — `src/vtuber/adapters/llm/config.py:8` — Подсекция `[llm.llamacpp]`: особенности llama-server.
- `GenerationConfig` — `src/vtuber/adapters/llm/config.py:23` — Подсекция `[llm.generation]`: длина и температура ответа диалога (T-07).
- `LLMConfig` — `src/vtuber/adapters/llm/config.py:30` — Какой бэкенд, где он, тайм-ауты (R-36) и параметры генерации.
- `ChildBinding` — `src/vtuber/adapters/llm/job_object.py:15` — Держит описатель задания: пока ядро живо, задание открыто; на других системах пусто.
- `LlamaCppLLM` — `src/vtuber/adapters/llm/llamacpp.py:41` — OpenAI-совместимый стрим + особенности llama-server.
- `OpenAICompatLLM` — `src/vtuber/adapters/llm/openai_compat.py:25` — Стрим ответа по HTTP/SSE; один httpx-клиент на всё время жизни (R-40, ADR-0007).
- `wire_messages` — `src/vtuber/adapters/llm/openai_compat.py:103` — Сообщения в формате OpenAI Chat API; без картинки — обычной строкой, как всегда.
- `check_status` — `src/vtuber/adapters/llm/openai_compat.py:128` — Переводит HTTP-код ошибки в доменную: 503 (модель грузится) — недоступность, иное — сбой.
- `LlamaServerConfig` — `src/vtuber/adapters/llm/server_process.py:31` — Секция `[llama_server]`: пути от корня проекта; `extra_args` — перед остальными флагами.
- `server_arguments` — `src/vtuber/adapters/llm/server_process.py:57` — Аргументы запуска; адрес берётся из `[llm].base_url`, чтобы они не разошлись.
- `LlamaServerProcess` — `src/vtuber/adapters/llm/server_process.py:85` — Живёт столько же, сколько контекст; выключен в конфиге — ничего не делает.
- `data_of` — `src/vtuber/adapters/llm/sse.py:12` — Полезная нагрузка строки `data: …` или None для пустых строк, комментариев и прочих полей.
- `delta_text` — `src/vtuber/adapters/llm/sse.py:19` — Текст дельты первого варианта ответа; пустая строка, если в порции текста нет.

## src/vtuber/adapters/memory
Адаптеры долговременной памяти: эмбеддеры и хранилища (ADR-0015).

- `E5Config` — `src/vtuber/adapters/memory/e5_embedder.py:32` — Настройки эмбеддера: каталог модели, её размерность, потоки CPU, длина и пакет.
- `OnnxSession` — `src/vtuber/adapters/memory/e5_embedder.py:42` — То, что нужно от `onnxruntime.InferenceSession`: прогон по именам входов.
- `E5Embedder` — `src/vtuber/adapters/memory/e5_embedder.py:52` — Реализует EmbedderPort; модель грузится один раз в `async with` (R-40).
- `BadNoteError` — `src/vtuber/adapters/memory/note_format.py:40` — Заметку не удалось разобрать; остальная память от этого не страдает.
- `fact_note_name` — `src/vtuber/adapters/memory/note_format.py:44` — Имя файла без расширения: читаемое начало текста и метка, чтобы имена не совпадали.
- `render_fact` — `src/vtuber/adapters/memory/note_format.py:51` — Заметка факта; ссылки дают связи в графе Obsidian.
- `parse_fact` — `src/vtuber/adapters/memory/note_format.py:79` — Факт из заметки; текст — всё до строки со ссылками, её пользователь может и удалить.
- `render_turn` — `src/vtuber/adapters/memory/note_format.py:105` — Ход в заметке чата; строки текста, похожие на разметку, экранируются.
- `parse_chat` — `src/vtuber/adapters/memory/note_format.py:129` — Ходы заметки чата по порядку; блок, правленный так, что не разбирается, пропускается.
- `render_host_note` — `src/vtuber/adapters/memory/note_format.py:148` — Заметка-узел: к ней сходятся факты, поэтому граф Obsidian не рассыпается на точки.
- `render_diary_line` — `src/vtuber/adapters/memory/note_format.py:153` — Строка дневника о новом факте.
- `ObsidianVault` — `src/vtuber/adapters/memory/obsidian_vault.py:60` — MemoryVaultPort; файловые операции — в потоке (R-34), сбой — `MemoryUnavailable`.
- `SqliteVecStore` — `src/vtuber/adapters/memory/sqlite_vec.py:42` — Реализует MemoryStorePort для векторов размерности `dimensions`; файл — `path`.

## src/vtuber/adapters/setup
Адаптеры мастера первого запуска: загрузка файлов.

- `HttpFetcherConfig` — `src/vtuber/adapters/setup/http_fetcher.py:16` — Подсекция `[setup.http]`: тайм-ауты соединения и ожидания следующей порции (R-36).
- `HttpFetcher` — `src/vtuber/adapters/setup/http_fetcher.py:23` — `FileFetcher`: сервер без поддержки Range отдаёт файл сначала, начало просто пропускается.

## src/vtuber/adapters/skills
Хранение выбора навыков (Этап 23, ADR-0043).

- `JsonSkillChoices` — `src/vtuber/adapters/skills/json_choices.py:11` — Реализует `SkillChoicesPort`; запись — через временный файл, сбой не оставит битый выбор.

## src/vtuber/adapters/stt
Адаптеры голосового ввода: распознавание и детектор речи (ADR-0016).

- `SenseVoiceConfig` — `src/vtuber/adapters/stt/sensevoice.py:33` — Секция `[stt.sound_model]`: работает на CPU, GPU остаётся диалогу.
- `sound_of` — `src/vtuber/adapters/stt/sensevoice.py:42` — Метка модели → звук; речь, дыхание и неизвестное — не звук для реакции.
- `SenseVoiceSounds` — `src/vtuber/adapters/stt/sensevoice.py:59` — Реализует `SoundClassifierPort`; модель живёт столько же, сколько контекст.
- `VadConfig` — `src/vtuber/adapters/stt/silero_vad.py:31` — Секция `[stt.vad]`: файл модели и потоки CPU (1 — окно короткое, больше не нужно).
- `SileroVad` — `src/vtuber/adapters/stt/silero_vad.py:46` — Реализует VadPort. Модели нет — отвечает `STTUnavailable`, не падает при старте.
- `SpeakerModelConfig` — `src/vtuber/adapters/stt/speaker_embedding.py:22` — Секция `[stt.speaker_model]`.
- `SherpaSpeakerEmbedder` — `src/vtuber/adapters/stt/speaker_embedding.py:41` — Реализует `SpeakerEmbedderPort`; модель грузится при первой фразе, в своём потоке.
- `WhisperConfig` — `src/vtuber/adapters/stt/whisper.py:34` — Секция `[stt.whisper]`.
- `WhisperSTT` — `src/vtuber/adapters/stt/whisper.py:70` — Реализует STTPort. Модели нет — не падает при старте, отвечает `STTUnavailable`.

## src/vtuber/adapters/tts
Адаптеры синтеза речи (TTSPort).

- `TTSConfig` — `src/vtuber/adapters/tts/config.py:14` — Секция `[tts]`.
- `CheckedTTS` — `src/vtuber/adapters/tts/fallback.py:16` — Основной движок: контекстный менеджер, который умеет сказать, почему он не готов.
- `ManagedTTS` — `src/vtuber/adapters/tts/fallback.py:34` — Запасной движок: загружается только тогда, когда он понадобился.
- `FallbackTTS` — `src/vtuber/adapters/tts/fallback.py:47` — Реализует TTSPort: движок выбирается один раз при старте.
- `KokoroConfig` — `src/vtuber/adapters/tts/kokoro.py:33` — Подсекция `[tts.kokoro]`.
- `KokoroLike` — `src/vtuber/adapters/tts/kokoro.py:48` — То, что нужно от `kokoro_onnx.Kokoro`: синтез фразы в float-сэмплы.
- `load_kokoro` — `src/vtuber/adapters/tts/kokoro.py:59` — Модель Kokoro и банк голосов.
- `to_pcm16` — `src/vtuber/adapters/tts/kokoro.py:70` — float32-сэмплы → PCM s16le.
- `KokoroTTS` — `src/vtuber/adapters/tts/kokoro.py:78` — Реализует TTSPort; модель грузится и прогревается один раз в `async with` (R-40).
- `PiperConfig` — `src/vtuber/adapters/tts/piper.py:28` — Подсекция `[tts.piper]`.
- `PiperChunk` — `src/vtuber/adapters/tts/piper.py:42` — Фрагмент `piper.AudioChunk`: PCM s16le моно.
- `PiperVoiceLike` — `src/vtuber/adapters/tts/piper.py:51` — То, что нужно от `piper.PiperVoice`: частота голоса и синтез по предложениям.
- `load_voice` — `src/vtuber/adapters/tts/piper.py:85` — Голос Piper: `.onnx` и рядом `.onnx.json`.
- `PiperTTS` — `src/vtuber/adapters/tts/piper.py:92` — Реализует TTSPort; голос грузится и прогревается один раз в `async with` (R-40).
- `SileroConfig` — `src/vtuber/adapters/tts/silero.py:38` — Подсекция `[tts.silero]`.
- `SileroModel` — `src/vtuber/adapters/tts/silero.py:52` — То, что нужно от модели Silero (`TTSModelMultiAcc`): синтез фразы в тензор float.
- `load_package` — `src/vtuber/adapters/tts/silero.py:63` — Модель из `.pt`-пакета Silero (официальный способ загрузки без torch.hub).
- `to_pcm` — `src/vtuber/adapters/tts/silero.py:71` — Тензор float [-1, 1] → PCM s16le; выход за шкалу обрезается, а не переворачивается.
- `SileroTTS` — `src/vtuber/adapters/tts/silero.py:79` — Реализует TTSPort; модель грузится один раз в `async with` (R-40).
- `VoiceServerConfig` — `src/vtuber/adapters/tts/voice_server.py:32` — Подсекция `[tts.voice_server]`.
- `VoiceServerTTS` — `src/vtuber/adapters/tts/voice_server.py:46` — Реализует TTSPort поверх `scripts/voice_server.py`.

## src/vtuber/application
Прикладной слой: сценарии диалога и конвейер ответа поверх портов.

## src/vtuber/application/chats
Чаты: каталог, категории, какой чат открыт (Этап 21, ADR-0037).

- `ChatDirectory` — `src/vtuber/application/chats/directory.py:39` — Список чатов и категорий; `changed` — кому сообщать о новом состоянии (UI).

## src/vtuber/application/conversation
Сценарий «ход диалога»: реплика → промпт → конвейер → история и события.

- `Branch` — `src/vtuber/application/conversation/branches.py:11` — Ветка — путь до листа: `title` — последняя реплика; `active` — текущий путь через неё.
- `Checkpoint` — `src/vtuber/application/conversation/branches.py:21` — Названное место в диалоге.
- `DialogueTree` — `src/vtuber/application/conversation/branches.py:28` — Хранит все ходы; история промпта — только путь до активного.
- `FirstOutputSink` — `src/vtuber/application/conversation/first_output.py:11` — Пропускает всё в `inner`; на первом выводе ответа зовёт `on_first` (THINKING → SPEAKING).
- `InitiativeConfig` — `src/vtuber/application/conversation/initiative.py:20` — Секция `[initiative]`: выключена по умолчанию, персонаж молчит, пока его не попросят.
- `InitiativeActions` — `src/vtuber/application/conversation/initiative.py:31` — `speak` возвращается, когда реплика прозвучала; `blocked` — занято: ход, речь, набор, фон.
- `Initiative` — `src/vtuber/application/conversation/initiative.py:39` — Считает тишину и говорит, когда её набралось; `user_input` обрывает реплику сразу.
- `play_performance` — `src/vtuber/application/conversation/performance.py:10` — Текст и эмоция — сразу, звук — по мере чтения; отмена закрывает источник.
- `ConversationService` — `src/vtuber/application/conversation/service.py:60` — Точка входа сценария «ход диалога» (docs/architecture.md, жизненный цикл хода).

## src/vtuber/application/language
Языковые пакеты изданий: что в ядре зависит от языка (Этап 20, ADR-0032).

- `LanguagePack` — `src/vtuber/application/language/pack.py:16` — Рамка промпта и служебные реплики, память, дикция голоса.

## src/vtuber/application/memory
Память витюбера: история разговора, её резюме и долговременные факты (Этап 10).

- `MemoryEditor` — `src/vtuber/application/memory/editor.py:13` — После правки индекс сверяется сразу: удалённый факт не должен попасть в следующий ответ.
- `MemoryControls` — `src/vtuber/application/memory/editor.py:55` — Что UI может делать с памятью.
- `ExtractedFact` — `src/vtuber/application/memory/fact_extractor.py:22` — Факт из ответа LLM; важность — как её оценила модель.
- `parse_facts` — `src/vtuber/application/memory/fact_extractor.py:37` — Факты из ответа модели; пробелы по краям текста срезаются.
- `FactExtractor` — `src/vtuber/application/memory/fact_extractor.py:56` — Ход → факты о пользователе одним запросом к LLM (низкая temperature — в `params`).
- `FactMemoryConfig` — `src/vtuber/application/memory/facts.py:21` — `dedup_score` — близость (косинус), от которой новый факт считается уже известным.
- `FactMemory` — `src/vtuber/application/memory/facts.py:27` — Факты о пользователе: извлечение (LLM), векторы (эмбеддер), хранилище.
- `MemoryKeeper` — `src/vtuber/application/memory/keeper.py:23` — По каждому записанному ходу: факты — в долговременную память, отрезанное — в резюме.
- `collect` — `src/vtuber/application/memory/llm_text.py:15` — Ответ LLM целиком (фоновым задачам стрим не нужен); поток закрывается при отмене.
- `strip_tags` — `src/vtuber/application/memory/llm_text.py:21` — Текст ответа без тегов эмоций.
- `MemoryEraser` — `src/vtuber/application/memory/privacy.py:12` — Сначала останавливает всё, что ещё может записать, и лишь потом удаляет.
- `needs_memory` — `src/vtuber/application/memory/retrieval_gate.py:26` — Реплика о прошлом разговоре или вопрос о самом пользователе.
- `is_factual_question` — `src/vtuber/application/memory/retrieval_gate.py:33` — Вопрос о мире, а не о пользователе: на нём цена выдумки выше, температура ниже.
- `RetrievalConfig` — `src/vtuber/application/memory/retrieval_gate.py:38` — Секция `[memory.retrieval]`.
- `TurnHints` — `src/vtuber/application/memory/retrieval_gate.py:53` — Что память добавляет ходу: справка в реплику и температура (None — обычная).
- `RecallSearch` — `src/vtuber/application/memory/retrieval_gate.py:61` — Чем искать факты: эмбеддер запроса и хранилище.
- `MemoryRecall` — `src/vtuber/application/memory/retrieval_gate.py:68` — Подсказки хода: факты из памяти, если гейт открыт; сбой памяти ход не задерживает.
- `ShortTermMemory` — `src/vtuber/application/memory/short_term.py:28` — История ходов для промпта (T-04).
- `Summarizer` — `src/vtuber/application/memory/summarizer.py:19` — Прежнее резюме + отрезанные сообщения → новое резюме одним запросом к LLM.
- `GatePatterns` — `src/vtuber/application/memory/texts.py:12` — Эвристики гейта поиска: о прошлом, о пользователе, вопрос, вопрос о мире, «я» в вопросе.
- `MemoryTexts` — `src/vtuber/application/memory/texts.py:23` — Строки фоновой памяти и справки хода.
- `TransferPaths` — `src/vtuber/application/memory/transfer.py:37` — Свои входящие и входящие другого издания (папка `inbox` рядом с базой памяти).
- `MemoryParts` — `src/vtuber/application/memory/transfer.py:47` — Заметки (источник правды), индекс и эмбеддер: после приёма индекс сверяется (ADR-0020).
- `FactTransfer` — `src/vtuber/application/memory/transfer.py:55` — Выгрузить свои факты другому изданию и принять присланные им.
- `TransferRequests` — `src/vtuber/application/memory/transfer.py:152` — Выгрузка по просьбе из UI — в простое (перевод занимает модель), итог — обратным вызовом.
- `VaultedFacts` — `src/vtuber/application/memory/vault_sync.py:31` — `MemoryStorePort`: сначала заметка, потом индекс; сбой записи не оставит факт без файла.
- `reconcile` — `src/vtuber/application/memory/vault_sync.py:56` — Приводит индекс к заметкам: правка главнее индекса, а заметка без разбора его не трогает.
- `VaultWatcher` — `src/vtuber/application/memory/vault_sync.py:88` — Замечает правки опросом: `watchdog` был бы новой зависимостью, а опрос стоит мало (замер).
- `ChatRecorder` — `src/vtuber/application/memory/vault_sync.py:157` — Пишет ходы в заметки своей задачей: подписчик шины только кладёт ход в очередь.
- `without_viewer_turns` — `src/vtuber/application/memory/viewer_filter.py:8` — Без реплик зрителей и ответов на них: иначе зритель попал бы в резюме, а оно — в промпт.

## src/vtuber/application/pipeline
Конвейер ответа: LLM → разбор тегов → нарезка фраз → TTS.

- `ChunkerConfig` — `src/vtuber/application/pipeline/chunker.py:23` — Секция `[pipeline.chunker]`.
- `SentenceChunker` — `src/vtuber/application/pipeline/chunker.py:51` — Один экземпляр на ход: `feed(дельта)` отдаёт готовые фразы, `flush()` — хвост.
- `PipelineConfig` — `src/vtuber/application/pipeline/config.py:8` — Секция `[pipeline]`: нарезка фраз и междометия-заглушки.
- `FillerConfig` — `src/vtuber/application/pipeline/filler.py:26` — Секция `[pipeline.filler]`.
- `FillerBank` — `src/vtuber/application/pipeline/filler.py:38` — Готовые к отдаче междометия; пустой банк (голос не загружен, выключено) — молчит.
- `AudioOut` — `src/vtuber/application/pipeline/filler.py:77` — Единственный писатель звука хода: ответ и междометие не перемешиваются.
- `Voice` — `src/vtuber/application/pipeline/reply_pipeline.py:21` — Голос хода: движок TTS, нарезка на фразы, междометия (T-17); без голоса — только текст.
- `ReplyPipeline` — `src/vtuber/application/pipeline/reply_pipeline.py:64` — Стримит ответ LLM получателю по мере генерации (T-01): ни одна стадия не ждёт конца.
- `Delivery` — `src/vtuber/application/pipeline/speaker.py:32` — Что кроме движка нужно речи хода: междометия, слушатель фраз, нормализатор издания.
- `Speaker` — `src/vtuber/application/pipeline/speaker.py:44` — Озвучивает фразы одного хода.
- `TextDelta` — `src/vtuber/application/pipeline/stream_parser.py:22` — Порция текста: `text` — для чата, `spoken_text` — для TTS (без эмодзи и разметки).
- `EmotionCue` — `src/vtuber/application/pipeline/stream_parser.py:34` — В ответе встретился тег эмоции; озвучивать нечего.
- `GestureCue` — `src/vtuber/application/pipeline/stream_parser.py:46` — В ответе встретился тег жеста; озвучивать нечего, речь он не задерживает.
- `StreamParser` — `src/vtuber/application/pipeline/stream_parser.py:60` — Разбирает дельты одного ответа по мере поступления (один экземпляр на ход).

## src/vtuber/application/prompting
Сборка промпта: персона, история, динамический блок — от неизменного к изменчивому (T-03).

- `ContextConfig` — `src/vtuber/application/prompting/context_budget.py:12` — Секция `[context]`.
- `ContextBudget` — `src/vtuber/application/prompting/context_budget.py:26` — Приближённый счёт токенов — без запроса к серверу, чтобы не тормозить горячий путь.
- `with_profile` — `src/vtuber/application/prompting/profile.py:21` — Персона с правилами профиля: без цензуры — разрешение и минимум; эфир — правила площадок.
- `FloorGuard` — `src/vtuber/application/prompting/profile.py:31` — `LLMPort`: реплика пересекает жёсткий минимум — отказ в образе без вызова модели.
- `Prompt` — `src/vtuber/application/prompting/prompt_builder.py:16` — Сообщения для LLM; первые `prefix_length` — неизменный префикс (персона и примеры).
- `PromptBuilder` — `src/vtuber/application/prompting/prompt_builder.py:23` — Строит промпт: [персона + примеры] → [история] → [справка + реплика] (T-03).
- `render_system_prompt` — `src/vtuber/application/prompting/prompt_builder.py:58` — Системный промпт персоны; `{emotions}` в правилах → теги всех эмоций из `Emotion`.
- `ProfileTexts` — `src/vtuber/application/prompting/texts.py:10` — Правила профиля содержания (ADR-0033) — дописываются рамкой к правилам персоны.
- `PromptTexts` — `src/vtuber/application/prompting/texts.py:77` — Строки рамки системного промпта и служебных реплик хода.

## src/vtuber/application/scheduler
Фоновые задачи в простое (T-13) и учёт видеопамяти моделей под управлением (ADR-0017).

- `SchedulerConfig` — `src/vtuber/application/scheduler/idle.py:31` — `idle_after_ms` — сколько тишины после хода считать простоем.
- `IdleJob` — `src/vtuber/application/scheduler/idle.py:38` — Фоновая задача: `run` можно звать повторно — отменённая задача перезапускается.
- `IdleScheduler` — `src/vtuber/application/scheduler/idle.py:45` — Очередь фоновых задач, которые выполняются по одной и только в простое (T-13).
- `ResourcesConfig` — `src/vtuber/application/scheduler/resource_types.py:11` — Секция `[resources]`: бюджет видеопамяти; `pinned` — имя → МБ, не вытесняется никогда.
- `Priority` — `src/vtuber/application/scheduler/resource_types.py:25` — Кто важнее при нехватке памяти; диалог закреплён и в очереди не стоит.
- `ModelState` — `src/vtuber/application/scheduler/resource_types.py:32` — Что с моделью сейчас.
- `ModelSpec` — `src/vtuber/application/scheduler/resource_types.py:42` — Модель под управлением: `vram_mb` — объём из замера (ADR-0017).
- `ModelStatus` — `src/vtuber/application/scheduler/resource_types.py:51` — Снимок одной модели для панели ресурсов.
- `ResourceSnapshot` — `src/vtuber/application/scheduler/resource_types.py:61` — Что сейчас в видеопамяти: для панели ресурсов (S-12.10).
- `ResourceManager` — `src/vtuber/application/scheduler/resources.py:51` — Единственное место, которое решает, какая модель сейчас в видеопамяти.

## src/vtuber/application/setup
Мастер первого запуска (S-13.2): что нужно этой машине и установка с проверкой сумм.

- `CatalogFile` — `src/vtuber/application/setup/catalog.py:11` — Файл компонента: откуда, куда (от корня) и как проверить; адрес закреплён на ревизии.
- `CatalogItem` — `src/vtuber/application/setup/catalog.py:20` — Компонент: модель или голос; `license` пользователь видит до согласия на загрузку.
- `SetupCatalog` — `src/vtuber/application/setup/catalog.py:39` — `config/catalog.toml`: компоненты, голоса и основная LLM.
- `Recommendation` — `src/vtuber/application/setup/catalog.py:55` — Совет этой машине; `warnings` показываются пользователю как есть.
- `recommend` — `src/vtuber/application/setup/catalog.py:63` — Всё, что помещается; обязательное советуется всегда, но с предупреждением.
- `InstallProgress` — `src/vtuber/application/setup/installer.py:30` — Сколько байт готово из общего числа, какой файл качается.
- `Installer` — `src/vtuber/application/setup/installer.py:57` — Ставит компоненты каталога в корень приложения; пути не выходят за пределы корня.
- `SetupState` — `src/vtuber/application/setup/wizard.py:20` — Что показать: нужен ли мастер, что на машине, что посоветовано и что уже стоит.
- `SetupChoice` — `src/vtuber/application/setup/wizard.py:30` — Что выбрал пользователь в мастере.
- `SetupWizard` — `src/vtuber/application/setup/wizard.py:37` — Ставит только то, что выбрал пользователь; повторный вызов продолжает с места разрыва.

## src/vtuber/application/skills
Навыки помощника (Этап 23, ADR-0043): реестр, гейты и счётчики.

- `SkillsConfig` — `src/vtuber/application/skills/config.py:8` — Файл выбора — свой у каждого издания: навыки английского издания свои.
- `SkillGate` — `src/vtuber/application/skills/gates.py:15` — Что гейтам нужно от реестра навыков.
- `EnabledCommands` — `src/vtuber/application/skills/gates.py:27` — Команды ведущего без выключенных: выключенная команда идёт к модели обычной репликой.
- `gated_stream` — `src/vtuber/application/skills/gates.py:49` — Реплики источника, пока навык включён; выключенный — реплики читаются и отбрасываются.
- `gated_hints` — `src/vtuber/application/skills/gates.py:67` — Встроенный навык справки (память): выключен — ход идёт без неё и без затрат на неё.
- `SkillRegistry` — `src/vtuber/application/skills/registry.py:21` — Навыки издания. Незагруженный плагин виден как навык «весь плагин», выключенный.

## src/vtuber/application/speech
Подготовка текста к синтезу речи: числа, сокращения, латиница, разметка (S-7.2).

- `Diction` — `src/vtuber/application/speech/diction.py:35` — Нормализатор фраз для голоса и сокращения, на точке которых фраза не режется.
- `normalize_english` — `src/vtuber/application/speech/english.py:141` — Фраза для английского TTS: только слова, пробелы и интонационные знаки.
- `english_integer` — `src/vtuber/application/speech/english_numbers.py:31` — «1234» → «one thousand two hundred thirty-four»; больше `MAX_SPOKEN` — по цифрам.
- `english_digits` — `src/vtuber/application/speech/english_numbers.py:53` — «007» → «zero zero seven»: номер, а не количество.
- `english_decimal` — `src/vtuber/application/speech/english_numbers.py:58` — «3», «14» → «three point one four».
- `english_ordinal` — `src/vtuber/application/speech/english_numbers.py:63` — «21» → «twenty-first».
- `english_year` — `src/vtuber/application/speech/english_numbers.py:76` — «1999» → «nineteen ninety-nine», «2024» → «twenty twenty-four», «2005» → «two thousand five».
- `spell` — `src/vtuber/application/speech/latin.py:39` — По названиям букв: «GPU» → «джи пи ю».
- `latin_word_to_russian` — `src/vtuber/application/speech/latin.py:58` — Одно латинское слово по-русски: словарь, аббревиатура по буквам или транслит.
- `transliterate_latin` — `src/vtuber/application/speech/latin.py:67` — Все латинские слова текста — по-русски; остальное без изменений.
- `normalize_for_speech` — `src/vtuber/application/speech/normalizer.py:102` — Фраза для TTS: только слова, пробелы и знаки препинания, задающие интонацию.
- `plural` — `src/vtuber/application/speech/numbers.py:46` — Форма слова после числа: 1 тысяча, 3 тысячи, 5 тысяч, 11 тысяч, 21 тысяча.
- `digits_to_words` — `src/vtuber/application/speech/numbers.py:69` — По цифрам: «007» → «ноль ноль семь».
- `integer_to_words` — `src/vtuber/application/speech/numbers.py:74` — Целое словами; `feminine` — род единиц («одна целая», «две десятых»).
- `decimal_to_words` — `src/vtuber/application/speech/numbers.py:91` — Дробь из цифр до и после разделителя: «3», «5» → «три целых пять десятых».

## src/vtuber/application/supervision
Самовосстановление (S-17.1, ADR-0021): наблюдатель за компонентами и обёртки голоса и слуха.

- `SupervisorConfig` — `src/vtuber/application/supervision/supervisor.py:27` — Секция `[supervisor]`: как часто проверять и сколько раз пытаться поднять компонент.
- `Supervised` — `src/vtuber/application/supervision/supervisor.py:52` — Компонент под наблюдением.
- `Supervisor` — `src/vtuber/application/supervision/supervisor.py:74` — Следит за каждым компонентом отдельно: падение одного не задерживает проверку другого.
- `FailureFlag` — `src/vtuber/application/supervision/watched.py:15` — Сбой замечен, но ещё не исправлен.
- `WatchedTTS` — `src/vtuber/application/supervision/watched.py:35` — `TTSPort`: движок молчит дольше `timeout_s` или недоступен — флаг и `TTSUnavailable`.
- `WatchedSTT` — `src/vtuber/application/supervision/watched.py:70` — `STTPort`: то же для распознавания; срок большой, на CPU длинная фраза идёт секунды.

## src/vtuber/application/tools
Справка хода от плагинов: результат инструмента попадает в промпт до генерации (S-12.4).

- `ToolContext` — `src/vtuber/application/tools/context.py:14` — Опрашивает инструменты параллельно; не успели или упали — ход идёт без них (приоритет 1).

## src/vtuber/application/voice
Голосовой ввод (Этап 11): нарезка речи на фразы, распознавание, перебивание.

- `AddressingConfig` — `src/vtuber/application/voice/addressing.py:27` — Подсекция `[stt.addressing]`: `always` — любая речь, `by_name` — только обращение.
- `name_pattern` — `src/vtuber/application/voice/addressing.py:38` — Обращение: имя в начале, можно после «эй», или в самом конце («как дела, Мика?»).
- `without_call` — `src/vtuber/application/voice/addressing.py:46` — Запрос без обращения: «Эй, Умник, какая погода?» → «какая погода?»; метка остаётся.
- `AddressedEvents` — `src/vtuber/application/voice/addressing.py:56` — Пропускает голосовые события, только если обратились по имени; имя из запроса вырезается.
- `addressed` — `src/vtuber/application/voice/addressing.py:112` — В режиме `always` обёртки нет: лишний шаг в горячем пути ни к чему.
- `looks_unfinished` — `src/vtuber/application/voice/completeness.py:64` — Обрыв видно по многоточию или последним словам; вопрос и восклицание — конец точно.
- `VoiceConfig` — `src/vtuber/application/voice/listener.py:43` — `interim_ms` — как часто считать промежуточную гипотезу; `min_phrase_ms` — короче не речь.
- `VoiceEvents` — `src/vtuber/application/voice/listener.py:52` — Кто получает голосовой ввод: шлюз (шлёт в UI и начинает ход) или тест.
- `VoiceListener` — `src/vtuber/application/voice/listener.py:68` — Очередь кадров и обработка окон; `feed` не ждёт моделей, `run` — задачей у владельца.
- `SegmenterConfig` — `src/vtuber/application/voice/segmenter.py:15` — Подсекция `[stt.segmenter]`.
- `SpeechStarted` — `src/vtuber/application/voice/segmenter.py:33` — Началась фраза.
- `BargeIn` — `src/vtuber/application/voice/segmenter.py:38` — Речь длится достаточно, чтобы перебить витюбера; один раз на фразу.
- `SpeechEnded` — `src/vtuber/application/voice/segmenter.py:43` — Фраза закончилась; `pcm` — вся фраза с паузой перед ней, без хвоста тишины.
- `Segmenter` — `src/vtuber/application/voice/segmenter.py:52` — Состояние одной линии звука; `feed` принимает окна длиной `window_ms`.
- `SoundsConfig` — `src/vtuber/application/voice/sounds.py:44` — Секция `[stt.sounds]`: выключена, пока не проверена точность на настоящих записях.
- `SoundActions` — `src/vtuber/application/voice/sounds.py:55` — `busy` — идёт ход, речь или фраза ведущего; `react` — сказать реплику в тишине.
- `loudness` — `src/vtuber/application/voice/sounds.py:62` — Громкость окна s16le, 0…1: на тишину модель не тратится.
- `SoundWatcher` — `src/vtuber/application/voice/sounds.py:70` — Собирает окна и разбирает только последнее: отставшая разметка никому не нужна.
- `SpeakersConfig` — `src/vtuber/application/voice/speakers.py:24` — Секция `[stt.speakers]`: порог сходства подобран на синтетике, на людях не проверен.
- `SpeakerTracker` — `src/vtuber/application/voice/speakers.py:43` — Голоса разговора: близкий отпечаток уточняет знакомый голос, далёкий заводит новый.
- `SpeakerLabeler` — `src/vtuber/application/voice/speakers.py:79` — Метка фразы или None: один голос, короткая фраза, сбой. Без метки реплика идёт как есть.
- `labelled` — `src/vtuber/application/voice/speakers.py:108` — Реплика с меткой говорящего: так она попадает и к модели, и в историю.

## src/vtuber/bootstrap
Корень композиции: конфиг, персона, сборка графа объектов и точка входа.

- `MemoryAccess` — `src/vtuber/bootstrap/chat_wiring.py:22` — Память открытого чата и всё для смены; поля меняются при переключении.
- `app_memory` — `src/vtuber/bootstrap/chat_wiring.py:40` — Память на время работы; `chats=False` — один разговор, как до Этапа 21 (терминал).
- `chat_profile` — `src/vtuber/bootstrap/chats.py:37` — Профиль памяти чата: у основного — прежний (данные на старых путях), у других — свой.
- `ChatRelay` — `src/vtuber/bootstrap/chats.py:42` — Пересылает ходы с общей шины на шину открытого чата.
- `ChatSwitcher` — `src/vtuber/bootstrap/chats.py:59` — Открытый чат и его смена; `run` — задача-владелец памяти, `switch` — просьба сменить.
- `MemoryConfig` — `src/vtuber/bootstrap/config.py:40` — Секция `[memory]`: фоновая память (Этап 10) — факты и резюме истории в простое.
- `SttConfig` — `src/vtuber/bootstrap/config.py:95` — Секция `[stt]`: голосовой ввод в `serve` (Этап 11, ADR-0016); модели — при первом кадре.
- `AppConfig` — `src/vtuber/bootstrap/config.py:129` — Корень конфига. Только агрегирует: каждую секцию описывает модуль, которому она нужна.
- `load_app_config` — `src/vtuber/bootstrap/config.py:154` — Читает конфиг издания из `<root>/config` поверх `env` (порядок — `edition_files`).
- `Core` — `src/vtuber/bootstrap/container.py:30` — Общие механизмы, которые получают все: шина событий и телеметрия.
- `Backends` — `src/vtuber/bootstrap/container.py:38` — Внешние движки хода: LLM обязательна, голос — только у шлюза (в терминале нет звука).
- `llm_backends` — `src/vtuber/bootstrap/container.py:49` — Реестр LLM-адаптеров: имя из `[llm].backend` → адаптер (асинхронный контекстный менеджер).
- `tts_backends` — `src/vtuber/bootstrap/container.py:60` — Реестр движков TTS: имя из `[tts].backend` → адаптер; `none` — без голоса (OCP).
- `Conversation` — `src/vtuber/bootstrap/container.py:79` — Собранный диалог: сервис хода, сборщик промпта (прогрев, T-06), история (фоновая память).
- `build_conversation` — `src/vtuber/bootstrap/container.py:89` — Собирает сервис хода; сборщик промпта и история отдаются наружу — прогреву и памяти.
- `EditionConfig` — `src/vtuber/bootstrap/edition.py:40` — Секция `[edition]`: задаётся файлом `config/editions/<id>.toml`, а не пользователем.
- `resolve_edition` — `src/vtuber/bootstrap/edition.py:49` — Издание из `--edition`, иначе из `VTUBER_EDITION__ID`, иначе `ru` (прежнее поведение).
- `edition_files` — `src/vtuber/bootstrap/edition.py:66` — Файлы издания; у `ru` мастер пишет прежний `setup.toml` и действуют все ключи `user.toml`.
- `check_edition` — `src/vtuber/bootstrap/edition.py:79` — Файл издания или переменная окружения не должны подменить выбранное издание.
- `ignored_user_keys` — `src/vtuber/bootstrap/edition.py:94` — Языковые ключи общего `user.toml`, которые в этом издании не действуют (предупреждение).
- `language_pack` — `src/vtuber/bootstrap/edition.py:115` — Языковой пакет по `[edition].language`.
- `edition_persona` — `src/vtuber/bootstrap/edition.py:132` — Персона из файла с правилами профиля содержания издания (ADR-0033).
- `warn_ignored_user_keys` — `src/vtuber/bootstrap/edition.py:144` — Предупреждение: ключи общего `user.toml` (он для `ru`) здесь не действуют.
- `LineSource` — `src/vtuber/bootstrap/main.py:67` — Откуда читать строки: `sys.stdin` или его тестовая замена.
- `Console` — `src/vtuber/bootstrap/main.py:74` — Ввод построчно в отдельном потоке — ожидание строки не блокирует цикл (R-34).
- `main` — `src/vtuber/bootstrap/main.py:87` — Код возврата: 0 — штатный выход, 1 — ошибка конфига, 2 — LLM недоступна (чат).
- `run` — `src/vtuber/bootstrap/main.py:316` — Запуск из консоли: `python -m vtuber [chat|serve] [--root путь]`.
- `SharedMemory` — `src/vtuber/bootstrap/memory.py:56` — Что общее у всех чатов (Этап 21): LLM фонового слота и e5 — грузятся один раз.
- `shared_memory` — `src/vtuber/bootstrap/memory.py:64` — Модели памяти на время работы приложения; память выключена — None.
- `chat_memory` — `src/vtuber/bootstrap/memory.py:78` — Память одного чата: своя база фактов, заметки, планировщик; история чата — в разговор.
- `background_memory` — `src/vtuber/bootstrap/memory.py:114` — Память одного чата вместе с моделями; выключена — пустой контекст (как до Этапа 21).
- `PersonaConfig` — `src/vtuber/bootstrap/persona.py:13` — Секция `[persona]`: путь к файлу персоны относительно корня проекта.
- `load_persona` — `src/vtuber/bootstrap/persona.py:40` — Читает и проверяет файл персоны; лишний или пропущенный ключ — ошибка.
- `ResourceModels` — `src/vtuber/bootstrap/plugins.py:40` — Менеджер ресурсов для плагинов: у ядра нет к нему прямого пути (ADR-0005).
- `PluginEnv` — `src/vtuber/bootstrap/plugins.py:61` — С чем плагины стартуют: секция конфига, шина, видеопамять, язык издания.
- `PluginServices` — `src/vtuber/bootstrap/plugins.py:71` — Что плагины дали ядру: живые списки — ядро читает их на каждой реплике.
- `running_plugins` — `src/vtuber/bootstrap/plugins.py:142` — Включённые (в конфиге и в панели «Навыки» — `wanted`) плагины работают на время контекста.
- `SetupConfig` — `src/vtuber/bootstrap/setup.py:18` — Секция `[setup]`: мастер включён только в поставке; при разработке модели кладут сами.
- `load_catalog` — `src/vtuber/bootstrap/setup.py:38` — Каталог компонентов.
- `render_choice` — `src/vtuber/bootstrap/setup.py:53` — TOML-файл из секций; строки в JSON совпадают со строками TOML, нужных нам значений хватит.
- `write_choice` — `src/vtuber/bootstrap/setup.py:64` — Заменяет файл целиком и атомарно: сбой на середине не оставит битый конфиг.
- `build_wizard` — `src/vtuber/bootstrap/setup.py:72` — Мастер на настоящей сети и диске.
- `core_skills` — `src/vtuber/bootstrap/skills.py:42` — Встроенные навыки: память всегда, инициатива — если она включена в конфиге.
- `open_skills` — `src/vtuber/bootstrap/skills.py:58` — Реестр с выбором пользователя и встроенными навыками.
- `connect_skills` — `src/vtuber/bootstrap/skills.py:65` — Навыки плагинов — в реестр; справка хода — через гейт; плагин можно запустить на ходу.
- `LlmSupervised` — `src/vtuber/bootstrap/supervision.py:21` — Сервер, запущенный ядром; внешний не наблюдается: поднять его ядро всё равно не может.
- `ReloadableTTS` — `src/vtuber/bootstrap/supervision.py:43` — Движок голоса, который загружается и выгружается контекстом.
- `TtsSupervised` — `src/vtuber/bootstrap/supervision.py:60` — Голос: сбой виден по флагу, поднять — значит загрузить модель заново и проверить её.
- `VoiceParts` — `src/vtuber/bootstrap/supervision.py:89` — Голос шлюза: движок (грузится при старте), его междометия и обёртка для наблюдателя.
- `build_voice` — `src/vtuber/bootstrap/supervision.py:98` — Голос из конфига; `none` — без голоса.
- `with_voice` — `src/vtuber/bootstrap/supervision.py:109` — Движки хода: конвейер получает обёртку, чтобы сбой голоса был замечен.
- `voice_input` — `src/vtuber/bootstrap/voice_input.py:148` — Подключает микрофон к шлюзу на время контекста; выключено в конфиге — кадры не нужны.
- `AppParts` — `src/vtuber/bootstrap/wiring.py:38` — Что шлюзу нужно от приложения, кроме сервиса хода.
- `connect_memory` — `src/vtuber/bootstrap/wiring.py:51` — Приватный режим работает и без памяти; редактор и очистка честно скажут, что её нет.
- `connect_branches` — `src/vtuber/bootstrap/wiring.py:62` — Дерево начинается с восстановленного разговора: его ветки тоже можно продолжить.
- `connect_panels` — `src/vtuber/bootstrap/wiring.py:72` — Всё, что UI может сделать помимо реплики.
- `connect_chat` — `src/vtuber/bootstrap/wiring.py:102` — Панели памяти и веток — к открытому чату: его факты, его история и шина его ходов.
- `connect_initiative` — `src/vtuber/bootstrap/wiring.py:108` — Персонаж сам заговаривает, только если это включили (S-15.1); фон памяти не прерывается.
- `connect_setup` — `src/vtuber/bootstrap/wiring.py:131` — Мастер есть только в поставке: при разработке модели кладут сами.
- `read_sources` — `src/vtuber/bootstrap/wiring.py:138` — Выключенный навык — его реплики не идут; плагин, включённый на ходу, читается сразу.

## src/vtuber/domain
Доменный слой: неизменяемые сущности и значения диалога, речи и эмоций.

- `is_chat_id` — `src/vtuber/domain/chat.py:14` — Идентификатор годится в имя папки и файла: без путей и особых символов.
- `ChatInfo` — `src/vtuber/domain/chat.py:20` — Чат в списке; `title` пустой — ещё не было реплик («Новый чат» в UI).
- `ChatCategory` — `src/vtuber/domain/chat.py:30` — Категория, которую создал пользователь.
- `ChatList` — `src/vtuber/domain/chat.py:38` — Весь каталог: чаты, категории и активный чат.
- `chat_title` — `src/vtuber/domain/chat.py:55` — Название чата из первой реплики: одна строка, не длиннее `MAX_TITLE`.
- `Role` — `src/vtuber/domain/dialogue.py:11` — Автор сообщения; значения совпадают с ролями OpenAI-совместимого API.
- `AttachedImage` — `src/vtuber/domain/dialogue.py:20` — Картинка к реплике (S-18.1); только в памяти и на один ход.
- `Message` — `src/vtuber/domain/dialogue.py:28` — Одно сообщение контекста LLM.
- `Turn` — `src/vtuber/domain/dialogue.py:37` — Завершённый ход: реплика пользователя и ответ витюбера.
- `Persona` — `src/vtuber/domain/dialogue.py:55` — Характер витюбера, задаётся файлом `personas/*.toml` без правки кода (FR-11).
- `EditionId` — `src/vtuber/domain/edition.py:6` — Издание выбирается до старта ядра: от него зависят файлы конфига и папка данных.
- `ContentProfile` — `src/vtuber/domain/edition.py:13` — Насколько персоне разрешено «всё» (ADR-0033); жёсткий минимум не зависит от профиля.
- `Emotion` — `src/vtuber/domain/emotion.py:10` — Единственный источник списка эмоций: из него строятся промпт персоны и разбор ответа.
- `Gesture` — `src/vtuber/domain/emotion.py:31` — Жест по смыслу фразы (S-18.4): тег как у эмоций, вид — в `mapping.json` модели.
- `parse_gesture` — `src/vtuber/domain/emotion.py:45` — Жест по тегу вида `<nod>` или None; регистр и пробелы — как у `parse_tag`.
- `parse_tag` — `src/vtuber/domain/emotion.py:56` — Возвращает эмоцию по тегу вида `<happy>` или None, если тег неизвестен или искажён.
- `VtuberError` — `src/vtuber/domain/errors.py:4` — Базовая ошибка приложения; сообщение говорит, что делать (R-45).
- `BackendUnavailable` — `src/vtuber/domain/errors.py:8` — Бэкенд не отвечает или не загружен.
- `LLMUnavailable` — `src/vtuber/domain/errors.py:12` — LLM-сервер недоступен.
- `ResourceUnavailable` — `src/vtuber/domain/errors.py:16` — Модели не хватило видеопамяти или она не загрузилась (ADR-0017); диалог не страдает.
- `SetupFailed` — `src/vtuber/domain/errors.py:20` — Мастер первого запуска не смог поставить компонент; текст показывается пользователю.
- `TTSUnavailable` — `src/vtuber/domain/errors.py:24` — Движок синтеза речи недоступен.
- `STTUnavailable` — `src/vtuber/domain/errors.py:28` — Распознавание речи или детектор недоступны: голосовой ввод молчит, чат работает.
- `MemoryUnavailable` — `src/vtuber/domain/errors.py:32` — Долговременная память недоступна (модель эмбеддингов или хранилище) — ход идёт без неё.
- `GenerationFailed` — `src/vtuber/domain/errors.py:36` — Бэкенд ответил, но генерация сорвалась посреди хода.
- `VisionUnavailable` — `src/vtuber/domain/errors.py:40` — Модель не приняла картинку: сервер запущен без проектора.
- `ProtocolError` — `src/vtuber/domain/errors.py:44` — Сообщение от UI не соответствует протоколу.
- `ConfigError` — `src/vtuber/domain/errors.py:48` — Конфигурация не читается или не проходит проверку; приложение не стартует.
- `TurnStateError` — `src/vtuber/domain/errors.py:52` — Недопустимый переход состояния хода — ошибка в логике сервиса, а не во внешнем мире.
- `CancelReason` — `src/vtuber/domain/events.py:12` — Почему ход прерван.
- `Component` — `src/vtuber/domain/events.py:21` — Бэкенд, о состоянии которого сообщается в UI.
- `BackendState` — `src/vtuber/domain/events.py:29` — Состояние бэкенда для статус-бара UI.
- `TurnStarted` — `src/vtuber/domain/events.py:38` — Ход начат: аватар сразу показывает «думаю» (T-17).
- `TurnRemembered` — `src/vtuber/domain/events.py:45` — Ход записан в историю; `dropped` — сообщения, отрезанные из неё при этом (T-04).
- `TurnFinished` — `src/vtuber/domain/events.py:56` — Ход завершён полностью.
- `TurnCancelled` — `src/vtuber/domain/events.py:63` — Ход прерван; UI сбрасывает аудиобуфер. `message` — что сказать пользователю при ошибке.
- `EmotionChanged` — `src/vtuber/domain/events.py:72` — В ответе встретился тег эмоции.
- `PhraseVoiced` — `src/vtuber/domain/events.py:80` — Фраза озвучена: зазвучит через `starts_in_s` и продлится `duration_s` (субтитры, Этап 12).
- `PerformanceRequested` — `src/vtuber/domain/events.py:93` — Плагин просит исполнить готовый звук (S-18.5).
- `TextShown` — `src/vtuber/domain/events.py:101` — Плагин просит показать текст в чате; озвучки у него нет (S-12.6).
- `SoundKind` — `src/vtuber/domain/events.py:108` — Звук вокруг, не речь (S-14.4).
- `SoundHeard` — `src/vtuber/domain/events.py:120` — Микрофон услышал звук; сам звук в событие не входит.
- `SearchSource` — `src/vtuber/domain/events.py:127` — Откуда взят ответ: заголовок и адрес страницы.
- `SourcesFound` — `src/vtuber/domain/events.py:135` — Инструмент нашёл источники для этого ответа: UI покажет ссылки (FR-25).
- `BackendNotice` — `src/vtuber/domain/events.py:142` — Сообщение пользователю о компоненте: упал, поднимается, снова работает (S-17.1).
- `ViewerBlocked` — `src/vtuber/domain/events.py:150` — Реплика зрителя похожа на атаку и не дошла до модели; ведущий видит это в UI (FR-31).
- `MetricRecorded` — `src/vtuber/domain/events.py:158` — Замер стадии хода; `turn_id` — None, если замер вне хода (например, прогрев).
- `BackendStatusChanged` — `src/vtuber/domain/events.py:167` — Бэкенд загрузился, упал или восстановился.
- `crosses_hard_floor` — `src/vtuber/domain/floor.py:30` — Реплика явно просит сексуальное содержание с участием несовершеннолетних.
- `GpuMemory` — `src/vtuber/domain/gpu.py:7` — Сколько видеопамяти всего и сколько занято всеми программами.
- `IncomingMessage` — `src/vtuber/domain/incoming.py:7` — Реплика из источника `source` (например, `twitch`) от автора `author`.
- `EmbedKind` — `src/vtuber/domain/memory.py:14` — Что кодируется: у e5 запрос и запоминаемый текст кодируются по-разному.
- `FactSource` — `src/vtuber/domain/memory.py:21` — Откуда факт: от этого зависит доверие к нему при ответе.
- `Fact` — `src/vtuber/domain/memory.py:33` — Одна запоминаемая мысль; `importance` 0…1 — что вспоминать в первую очередь.
- `VaultScan` — `src/vtuber/domain/memory.py:55` — Заметки фактов: разобранные и те, что сейчас не читаются (их имена).
- `FactHit` — `src/vtuber/domain/memory.py:63` — Найденный факт; `score` — косинусная близость к запросу, −1…1, больше — ближе.
- `SkillInfo` — `src/vtuber/domain/skill.py:17` — Описание навыка для панели: тексты — на языке издания.
- `SkillStats` — `src/vtuber/domain/skill.py:34` — Счётчики за сессию: сколько раз навык дал результат, средняя задержка, сколько не успел.
- `SkillState` — `src/vtuber/domain/skill.py:56` — Навык в панели: описание, включён ли, загружен ли его плагин, счётчики.
- `plugin_skill` — `src/vtuber/domain/skill.py:65` — Навык «весь плагин»: так выглядит плагин, который своих навыков не объявил.
- `AudioFormat` — `src/vtuber/domain/speech.py:11` — Формат звука: PCM s16le, моно — так звук передаётся в UI (ADR-0003).
- `AudioChunk` — `src/vtuber/domain/speech.py:23` — Непрерывный фрагмент PCM в формате `format`.
- `TurnState` — `src/vtuber/domain/turn_state.py:10` — Где сейчас ход: ждём реплику, думаем, говорим, прерваны.
- `next_state` — `src/vtuber/domain/turn_state.py:30` — Возвращает `target`, если переход из `current` разрешён.
- `ViewerStyle` — `src/vtuber/domain/viewer.py:29` — Подпись реплики зрителя и имя автора по умолчанию на языке издания (Этап 20).
- `looks_like_attack` — `src/vtuber/domain/viewer.py:93` — Явная попытка отменить правила, сменить роль, выманить настройки или подделать разметку.
- `viewer_line` — `src/vtuber/domain/viewer.py:101` — Реплика зрителя для промпта и истории; подделать кавычки и подпись из текста нельзя.
- `is_viewer_line` — `src/vtuber/domain/viewer.py:108` — Реплика в истории — от зрителя, а не от ведущего (подпись любого издания).
- `without_viewer_prefix` — `src/vtuber/domain/viewer.py:113` — Реплика без подписи зрителя — для заголовков веток и т.п.

## src/vtuber/gateway
Шлюз: протокол UI ↔ Ядро, кодек, WebSocket-сервер и терминальный чат (M1).

- `shown_text` — `src/vtuber/gateway/branch_bridge.py:19` — Ответ в истории хранится с тегами эмоций; в чате их быть не должно.
- `BranchBridge` — `src/vtuber/gateway/branch_bridge.py:44` — Переход отменяет идущий ответ и заменяет историю промпта: модель видит только новую ветку.
- `ChatsBridge` — `src/vtuber/gateway/chats_bridge.py:18` — Пока чат переключается, новые действия ждут: две смены сразу память не выдержит.
- `AudioFrame` — `src/vtuber/gateway/codec.py:24` — Разобранный аудиокадр.
- `MicFrame` — `src/vtuber/gateway/codec.py:33` — Разобранный кадр микрофона: PCM s16le моно от UI (Этап 11).
- `encode_mic_frame` — `src/vtuber/gateway/codec.py:40` — Кадр микрофона: 8 байт заголовка + PCM; так его собирает UI (`core/frames.ts`).
- `decode_mic_frame` — `src/vtuber/gateway/codec.py:50` — Разбирает бинарный кадр от UI; проверка один раз на границе.
- `decode_inbound` — `src/vtuber/gateway/codec.py:71` — Сообщение от UI; проверка один раз на границе (принцип 6 архитектуры).
- `encode_outbound` — `src/vtuber/gateway/codec.py:86` — JSON-строка сообщения для UI (сериализация pydantic-core, без лишних пробелов).
- `encode_audio_frame` — `src/vtuber/gateway/codec.py:91` — Бинарный кадр: 16 байт заголовка + PCM s16le моно; `seq` по модулю 2^16.
- `decode_audio_frame` — `src/vtuber/gateway/codec.py:99` — Разбирает аудиокадр (тесты; кадры микрофона — Этап 11).
- `ExternalTurns` — `src/vtuber/gateway/external_turns.py:17` — Отвечает на реплики по одной и только в тишине: зритель не обрывает речь витюбера.
- `MemoryBridge` — `src/vtuber/gateway/memory_bridge.py:18` — Список запрашивается только при открытой панели: чтение заметок не должно идти просто так.
- `Panels` — `src/vtuber/gateway/panels.py:44` — Панель не подключена — её сообщения просто не нужны.
- `PrivacyBridge` — `src/vtuber/gateway/privacy_bridge.py:17` — Режим держит сервис хода, а UI получает его состояние при каждом подключении.
- `turn_ref` — `src/vtuber/gateway/protocol.py:43` — Номер хода в JSON-сообщениях: `t-000042` (в аудиокадре — uint64).
- `ErrorCode` — `src/vtuber/gateway/protocol.py:48` — Что пошло не так — UI выбирает реакцию по коду, текст показывает пользователю.
- `SendData` — `src/vtuber/gateway/protocol.py:57` — Реплика пользователя.
- `TypingData` — `src/vtuber/gateway/protocol.py:63` — Черновик реплики, пока пользователь печатает; пустой — поле очищено.
- `DeltaData` — `src/vtuber/gateway/protocol.py:69` — Порция текста ответа.
- `EmotionData` — `src/vtuber/gateway/protocol.py:75` — Эмоция аватара; `intensity` 0…1 (затухание — Этап 8).
- `CancelledData` — `src/vtuber/gateway/protocol.py:82` — Почему ход прерван; `message` — текст ошибки при `reason == "error"`.
- `SpanData` — `src/vtuber/gateway/protocol.py:89` — Замер стадии хода для панели метрик (FR-15).
- `StatusData` — `src/vtuber/gateway/protocol.py:96` — Состояние бэкенда для статус-бара.
- `ErrorData` — `src/vtuber/gateway/protocol.py:103` — Ошибка для пользователя.
- `ChatSend` — `src/vtuber/gateway/protocol.py:110` — UI → Ядро: новая реплика; прерывает текущий ход.
- `ChatCancel` — `src/vtuber/gateway/protocol.py:118` — UI → Ядро: остановить ответ.
- `InputTyping` — `src/vtuber/gateway/protocol.py:126` — UI → Ядро: черновик реплики (с дебаунсом ~300 мс) — прогрев кэша LLM, T-05.
- `TurnStartedMessage` — `src/vtuber/gateway/protocol.py:157` — Ядро → UI: ход начат — аватар «думает» (T-17).
- `ChatDelta` — `src/vtuber/gateway/protocol.py:171` — Ядро → UI: порция текста ответа.
- `AvatarEmotion` — `src/vtuber/gateway/protocol.py:185` — Ядро → UI: сменить выражение аватара.
- `TurnFinishedMessage` — `src/vtuber/gateway/protocol.py:199` — Ядро → UI: ответ закончен полностью.
- `TurnCancelledMessage` — `src/vtuber/gateway/protocol.py:213` — Ядро → UI: ход прерван — UI сбрасывает аудиобуфер.
- `MetricsSpan` — `src/vtuber/gateway/protocol.py:227` — Ядро → UI: замер стадии; `turn` — None вне хода (прогрев).
- `Status` — `src/vtuber/gateway/protocol.py:241` — Ядро → UI: состояние бэкенда (вне хода).
- `InputBargeIn` — `src/vtuber/gateway/protocol.py:254` — Ядро → UI: пользователь заговорил — оборвать голос витюбера сразу (Этап 11).
- `InputHypothesis` — `src/vtuber/gateway/protocol.py:267` — Ядро → UI: промежуточный текст фразы пользователя.
- `InputFinal` — `src/vtuber/gateway/protocol.py:280` — Ядро → UI: распознанная фраза — реплика пользователя в чате; за ней начнётся ход.
- `ErrorMessage` — `src/vtuber/gateway/protocol.py:293` — Ядро → UI: ошибка; `turn` — None, если не относится к ходу (битое сообщение).
- `AttachmentData` — `src/vtuber/gateway/protocol_attachment.py:8` — Заголовок и текст.
- `ChatAttachment` — `src/vtuber/gateway/protocol_attachment.py:15` — Ядро → UI: показать текст отдельным сообщением; озвучки у него нет.
- `GestureData` — `src/vtuber/gateway/protocol_avatar.py:9` — Какой жест показать.
- `AvatarGesture` — `src/vtuber/gateway/protocol_avatar.py:15` — Ядро → UI: жест по смыслу фразы; модель без такого жеста его пропускает (S-18.4).
- `ProtocolModel` — `src/vtuber/gateway/protocol_base.py:13` — База сообщений: неизменяемы, лишнее поле — ошибка протокола.
- `EmptyData` — `src/vtuber/gateway/protocol_base.py:19` — Сообщение без полезной нагрузки.
- `BranchGoData` — `src/vtuber/gateway/protocol_branches.py:8` — К какой реплике вернуться.
- `BranchGo` — `src/vtuber/gateway/protocol_branches.py:14` — UI → Ядро: вернуться к реплике; следующая реплика начнёт новую ветку.
- `BranchCheckpointData` — `src/vtuber/gateway/protocol_branches.py:22` — Имя контрольной точки.
- `BranchCheckpoint` — `src/vtuber/gateway/protocol_branches.py:28` — UI → Ядро: запомнить текущее место под именем.
- `BranchMessageData` — `src/vtuber/gateway/protocol_branches.py:36` — Реплика активной ветки; у реплик пользователя `turn` — None.
- `BranchData` — `src/vtuber/gateway/protocol_branches.py:44` — Ветка: её последняя реплика и длина; `active` — текущий путь идёт через неё.
- `CheckpointData` — `src/vtuber/gateway/protocol_branches.py:53` — Контрольная точка.
- `BranchStateData` — `src/vtuber/gateway/protocol_branches.py:60` — Активный путь, все ветки и контрольные точки.
- `BranchState` — `src/vtuber/gateway/protocol_branches.py:69` — Ядро → UI: состояние диалога после перехода или при подключении.
- `ChatActionData` — `src/vtuber/gateway/protocol_chats.py:21` — Что сделать: `id` — чат или категория, `name` — название, `category` — куда положить.
- `ChatAction` — `src/vtuber/gateway/protocol_chats.py:30` — UI → Ядро: действие со списком чатов.
- `ChatItemData` — `src/vtuber/gateway/protocol_chats.py:38` — Чат в списке; пустое `title` — «Новый чат» на языке интерфейса.
- `CategoryData` — `src/vtuber/gateway/protocol_chats.py:47` — Категория.
- `ChatsData` — `src/vtuber/gateway/protocol_chats.py:54` — Весь список; `switching` — память переключается, ввод лучше подождать.
- `ChatsState` — `src/vtuber/gateway/protocol_chats.py:64` — Ядро → UI: список чатов после любого изменения и при подключении.
- `WatchData` — `src/vtuber/gateway/protocol_extras.py:11` — Открыта ли панель ресурсов.
- `ResourcesWatch` — `src/vtuber/gateway/protocol_extras.py:17` — UI → Ядро: панель ресурсов открыли или закрыли; закрытая ничего не считает.
- `InstallData` — `src/vtuber/gateway/protocol_extras.py:25` — Что выбрал пользователь в мастере.
- `SetupInstall` — `src/vtuber/gateway/protocol_extras.py:32` — UI → Ядро: согласие на загрузку; без этого сообщения ничего не скачивается (S-13.2).
- `SetupCancel` — `src/vtuber/gateway/protocol_extras.py:40` — UI → Ядро: прервать загрузку; скачанное продолжится при следующей попытке.
- `PinnedModelData` — `src/vtuber/gateway/protocol_extras.py:48` — Закреплённая модель: основная LLM, распознавание речи.
- `ManagedModelData` — `src/vtuber/gateway/protocol_extras.py:55` — Модель под управлением менеджера; `waiting_reason` — почему ждёт.
- `ResourcesData` — `src/vtuber/gateway/protocol_extras.py:66` — Снимок видеопамяти: `limit_mb` учитывает другие программы, `capacity_mb` — только конфиг.
- `ResourcesMessage` — `src/vtuber/gateway/protocol_extras.py:76` — Ядро → UI: снимок для панели ресурсов, только пока она открыта (S-12.10).
- `SetupItemData` — `src/vtuber/gateway/protocol_extras.py:108` — Компонент в мастере; `license` пользователь видит до согласия.
- `SetupData` — `src/vtuber/gateway/protocol_extras.py:120` — Состояние мастера: `gpu_total_mb` — None, если карта NVIDIA не найдена.
- `SetupStateMessage` — `src/vtuber/gateway/protocol_extras.py:131` — Ядро → UI: нужен ли мастер и что он предлагает; приходит при подключении.
- `ProgressData` — `src/vtuber/gateway/protocol_extras.py:166` — Сколько байт готово из общего числа и какой файл качается.
- `SetupProgress` — `src/vtuber/gateway/protocol_extras.py:174` — Ядро → UI: ход загрузки.
- `FinishedData` — `src/vtuber/gateway/protocol_extras.py:187` — Итог установки: `problem` — None, если всё поставлено.
- `SetupFinished` — `src/vtuber/gateway/protocol_extras.py:193` — Ядро → UI: установка закончена; после успеха приложение перезапускается.
- `BlockedData` — `src/vtuber/gateway/protocol_extras.py:206` — Кто и что написал.
- `ViewerBlockedMessage` — `src/vtuber/gateway/protocol_extras.py:213` — Ядро → UI: реплика зрителя заблокирована как атака; ведущий решает, что делать (FR-31).
- `NoticeData` — `src/vtuber/gateway/protocol_extras.py:226` — Текст для пользователя.
- `BackendNoticeMessage` — `src/vtuber/gateway/protocol_extras.py:232` — Ядро → UI: компонент упал, поднимается или снова работает (S-17.1).
- `SourceData` — `src/vtuber/gateway/protocol_extras.py:245` — Откуда взят ответ.
- `SourcesData` — `src/vtuber/gateway/protocol_extras.py:252` — Источники текущего ответа.
- `ChatSources` — `src/vtuber/gateway/protocol_extras.py:258` — Ядро → UI: инструмент нашёл источники для этого ответа (FR-25).
- `PrivacySetData` — `src/vtuber/gateway/protocol_memory.py:10` — Включить или выключить приватный режим.
- `PrivacySet` — `src/vtuber/gateway/protocol_memory.py:16` — UI → Ядро: разговор не запоминается (S-17.2).
- `EraseData` — `src/vtuber/gateway/protocol_memory.py:24` — `confirm` — пользователь подтвердил: без него очистка не выполняется.
- `MemoryErase` — `src/vtuber/gateway/protocol_memory.py:30` — UI → Ядро: удалить всю память.
- `PrivacyStateData` — `src/vtuber/gateway/protocol_memory.py:38` — Режим и можно ли очистить память (она может быть выключена).
- `PrivacyState` — `src/vtuber/gateway/protocol_memory.py:45` — Ядро → UI: состояние режима; приходит при подключении и после переключения.
- `ErasedData` — `src/vtuber/gateway/protocol_memory.py:58` — `problem` — None, если всё удалено.
- `MemoryErased` — `src/vtuber/gateway/protocol_memory.py:64` — Ядро → UI: итог очистки.
- `MemoryList` — `src/vtuber/gateway/protocol_memory.py:77` — UI → Ядро: открыта панель памяти, нужен список.
- `FactSaveData` — `src/vtuber/gateway/protocol_memory.py:85` — Новый текст факта.
- `MemoryFactSave` — `src/vtuber/gateway/protocol_memory.py:92` — UI → Ядро: исправить факт.
- `FactDeleteData` — `src/vtuber/gateway/protocol_memory.py:100` — Какой факт удалить.
- `MemoryFactDelete` — `src/vtuber/gateway/protocol_memory.py:106` — UI → Ядро: удалить факт.
- `FactData` — `src/vtuber/gateway/protocol_memory.py:114` — Факт с его источником.
- `FactsData` — `src/vtuber/gateway/protocol_memory.py:124` — Список фактов; `problem` — что не удалось сделать.
- `MemoryFacts` — `src/vtuber/gateway/protocol_memory.py:131` — Ядро → UI: факты памяти (S-16.2).
- `MemoryTransfer` — `src/vtuber/gateway/protocol_memory.py:154` — UI → Ядро: перенести факты о пользователе в другое издание (S-20.10).
- `TransferredData` — `src/vtuber/gateway/protocol_memory.py:162` — Итог переноса: сколько фактов выгружено, или текст ошибки.
- `MemoryTransferred` — `src/vtuber/gateway/protocol_memory.py:169` — Ядро → UI: перенос закончен (идёт в простое, поэтому — отдельным сообщением).
- `VisibilityData` — `src/vtuber/gateway/protocol_presence.py:8` — Видно ли окно.
- `WindowVisibility` — `src/vtuber/gateway/protocol_presence.py:14` — UI → Ядро: окно свернули или вернули; свёрнутому персонаж сам не заговорит (S-15.1).
- `EditionData` — `src/vtuber/gateway/protocol_presence.py:22` — Издание ядра (Этап 20, ADR-0032): язык интерфейса и профиль содержания.
- `AppEdition` — `src/vtuber/gateway/protocol_presence.py:31` — Ядро → UI при подключении: в каком издании запущено ядро; UI сверяет с выбором на экране.
- `SkillsActionData` — `src/vtuber/gateway/protocol_skills.py:9` — `list` — прислать список (и найти установленные плагины); `set` — включить или выключить.
- `SkillsAction` — `src/vtuber/gateway/protocol_skills.py:17` — UI → Ядро: действие в панели «Навыки».
- `SkillData` — `src/vtuber/gateway/protocol_skills.py:25` — Навык в панели: тексты на языке издания, флаги, состояние и счётчики за сессию.
- `SkillsData` — `src/vtuber/gateway/protocol_skills.py:45` — Все навыки; `problem` — почему не получилось последнее действие.
- `SkillsState` — `src/vtuber/gateway/protocol_skills.py:52` — Ядро → UI: список навыков по запросу и после переключения.
- `ImageData` — `src/vtuber/gateway/protocol_vision.py:12` — Картинка; UI уменьшает её заранее.
- `SendImageData` — `src/vtuber/gateway/protocol_vision.py:19` — Реплика с картинкой.
- `ChatSendImage` — `src/vtuber/gateway/protocol_vision.py:26` — UI → Ядро: новая реплика с картинкой; прерывает текущий ход, как `chat.send`.
- `ResourcesFeed` — `src/vtuber/gateway/resources_feed.py:15` — Закрытая панель ничего не считает: задачи нет, пока UI не попросит.
- `GatewayConfig` — `src/vtuber/gateway/server.py:64` — Секция `[gateway]`: где слушать UI (только localhost, ADR-0002).
- `GatewayServer` — `src/vtuber/gateway/server.py:71` — Шлюз для UI: `async with GatewayServer(...) as server: await server.serve_forever()`.
- `SetupBridge` — `src/vtuber/gateway/setup_bridge.py:22` — Переводит сообщения UI в вызовы мастера; ход установки шлёт реже, чем приходят данные.
- `WsReplySink` — `src/vtuber/gateway/sink.py:15` — ReplySink для WebSocket: текст → `chat.delta`, эмоция → `avatar.emotion`, звук → кадр.
- `SkillsBridge` — `src/vtuber/gateway/skills_bridge.py:15` — Действия по одному: включение плагина на ходу не должно пересечься со вторым.
- `TerminalSink` — `src/vtuber/gateway/terminal.py:29` — ReplySink для консоли: печатает ответ по мере генерации и помнит время первой порции.
- `TerminalChat` — `src/vtuber/gateway/terminal.py:69` — Цикл чата: строка → ход; новая строка во время ответа прерывает его (T-14).
- `VoiceBridge` — `src/vtuber/gateway/voice_bridge.py:17` — Реализует `VoiceEvents`: перебивание, гипотезы в UI, финальная фраза — новый ход.

## src/vtuber/kernel
Общие механизмы ядра: шина событий, реестр, телеметрия, конфиг, логи.

- `EventBus` — `src/vtuber/kernel/bus.py:15` — Доставляет событие подписчикам его точного типа (не подклассов), параллельно.
- `ConfigSection` — `src/vtuber/kernel/config.py:21` — База секции конфига: неизменяема, лишний ключ — ошибка (опечатка не пройдёт молча).
- `ConfigFiles` — `src/vtuber/kernel/config.py:32` — Файлы конфигурации: `default` и `edition` (если задан) обязательны, остальные — если есть.
- `load_config` — `src/vtuber/kernel/config.py:55` — Собирает конфиг из файлов и окружения и проверяет его моделью `model`.
- `current_turn` — `src/vtuber/kernel/context.py:14` — Номер текущего хода или None вне хода; чтение — десятки наносекунд (горячий путь).
- `turn_context` — `src/vtuber/kernel/context.py:20` — Внутри блока ход `turn_id` — текущий для метрик, а логи несут поле `turn_id`.
- `LoggingConfig` — `src/vtuber/kernel/logging.py:16` — Секция `[logging]`; `file` открывает bootstrap (относительно корня проекта).
- `configure_logging` — `src/vtuber/kernel/logging.py:23` — Настраивает structlog: одна JSON-строка на событие в `stream`.
- `logging_to` — `src/vtuber/kernel/logging.py:45` — Логи идут в `stream` на время блока; на выходе — настройка по умолчанию.
- `get_logger` — `src/vtuber/kernel/logging.py:58` — Логгер модуля; имя попадает в поле `module` каждого события.
- `ContextTool` — `src/vtuber/kernel/plugin.py:39` — Инструмент, его срок (`None` — обычный короткий срок из `[plugins]`) и навык (ADR-0043).
- `PluginsConfig` — `src/vtuber/kernel/plugin.py:53` — Секция `[plugins]`: что включено и настройки каждого плагина в `settings.<имя>`.
- `LoadableModel` — `src/vtuber/kernel/plugin.py:66` — Модель, которую можно загрузить в видеопамять и выгрузить.
- `ModelHost` — `src/vtuber/kernel/plugin.py:78` — Менеджер видеопамяти для плагинов; сам он живёт выше ядра (ADR-0005).
- `PluginContext` — `src/vtuber/kernel/plugin.py:88` — Доступ плагина к ядру: подписка на события, своя секция конфига, логгер.
- `Plugin` — `src/vtuber/kernel/plugin.py:250` — Плагин: entry point группы `vtuber.plugins` указывает на его класс или фабрику.
- `Registry` — `src/vtuber/kernel/registry.py:8` — Имя → фабрика `A → T`; например, `Registry[TTSConfig, TTSPort]` для движков TTS.
- `TelemetryConfig` — `src/vtuber/kernel/telemetry.py:23` — Секция `[telemetry]`; `traces_file` открывает bootstrap (относительно корня проекта).
- `Telemetry` — `src/vtuber/kernel/telemetry.py:29` — Замеряет стадии хода и отдаёт метрики в шину фоновой задачей `run`.
- `Span` — `src/vtuber/kernel/telemetry.py:63` — Контекстный менеджер одного замера; создаётся `Telemetry.span`.
- `TraceWriter` — `src/vtuber/kernel/telemetry.py:88` — Подписчик шины: пишет каждую метрику JSON-строкой в поток (`logs/traces.jsonl`).

## src/vtuber/ports
Порты: Protocol-интерфейсы, через которые ядро обращается к внешнему миру.

- `ChatCatalogPort` — `src/vtuber/ports/chats.py:8` — Каталог чатов издания. Ошибки доступа к диску — `MemoryUnavailable`.
- `MessageSource` — `src/vtuber/ports/incoming.py:9` — Поток реплик: чат стрима, тестовый фейк. Сам восстанавливает соединение.
- `GenerationParams` — `src/vtuber/ports/llm.py:11` — Параметры генерации; значения приходят из конфига (`[llm.generation]`, ADR-0006).
- `LLMPort` — `src/vtuber/ports/llm.py:19` — Локальная LLM; адаптеры бросают только доменные ошибки (R-43).
- `EmbedderPort` — `src/vtuber/ports/memory.py:14` — Тексты → векторы единичной длины.
- `MemoryStorePort` — `src/vtuber/ports/memory.py:36` — Факты с векторами: добавить и найти ближайшие.
- `MemoryVaultPort` — `src/vtuber/ports/memory.py:83` — Заметки — источник истины памяти (ADR-0020); контракт — `test_vault_contract.py`.
- `ManagedModel` — `src/vtuber/ports/resources.py:8` — Модель, которую можно загрузить в видеопамять и выгрузить по требованию.
- `GpuProbe` — `src/vtuber/ports/resources.py:18` — Фактическая занятость видеопамяти (ADR-0018).
- `FileFetcher` — `src/vtuber/ports/setup.py:7` — Откуда мастер берёт файлы; сбой — `SetupFailed` с понятным текстом.
- `ReplySink` — `src/vtuber/ports/sink.py:8` — Получатель результатов одного хода; конвейер не знает, что за ним.
- `SkillChoicesPort` — `src/vtuber/ports/skills.py:7` — Выбор пользователя поверх конфига: id навыка → включён. Ошибки диска — `ConfigError`.
- `SoundClassifierPort` — `src/vtuber/ports/stt.py:12` — Какой звук в окне, кроме речи (S-14.4).
- `SpeakerEmbedderPort` — `src/vtuber/ports/stt.py:26` — Отпечаток голоса фразы (S-14.3): у одного человека отпечатки близки.
- `VadPort` — `src/vtuber/ports/stt.py:40` — Детектор речи: окно PCM → вероятность, что это речь.
- `STTPort` — `src/vtuber/ports/stt.py:72` — Распознавание отрезка речи.
- `TTSPort` — `src/vtuber/ports/tts.py:9` — Движок TTS; адаптеры бросают только доменные ошибки (R-43).

## ui/src/app
—

- `App.svelte` — `ui/src/app/App.svelte:1` — —
- `wasOverlay` — `ui/src/app/restoreWindow.ts:15` — Была ли включена старая запись «поверх стола».
- `restoreWindow` — `ui/src/app/restoreWindow.ts:27` — —
- `DEFAULT_RATIO` — `ui/src/app/split.ts:7` — Чат 2 : сцена 3 — как в каркасе S-5.1.
- `MIN_CHAT_PX` — `ui/src/app/split.ts:9` — Уже — чат не читается, сцена теряет модель.
- `MIN_STAGE_PX` — `ui/src/app/split.ts:10` — —
- `KEYBOARD_STEP` — `ui/src/app/split.ts:12` — Шаг стрелками на разделителе — доступность с клавиатуры.
- `RatioStorage` — `ui/src/app/split.ts:17` — Минимальное хранилище: в тестах — Map-подобная подмена.
- `clampRatio` — `ui/src/app/split.ts:20` — Доля в пределах, при которых обе панели не уже своего минимума.
- `ratioAt` — `ui/src/app/split.ts:30` — Доля по положению указателя внутри раскладки.
- `loadRatio` — `ui/src/app/split.ts:35` — Сохранённая доля или умолчание; битое значение или недоступное хранилище — умолчание.
- `saveRatio` — `ui/src/app/split.ts:45` — Запомнить долю; ошибка хранилища (переполнено, запрещено) не ломает раскладку.
- `SplitLayout.svelte` — `ui/src/app/SplitLayout.svelte:1` — —
- `StageBadges.svelte` — `ui/src/app/StageBadges.svelte:1` — —
- `Tone` — `ui/src/app/status.ts:8` — —
- `Indicator` — `ui/src/app/status.ts:10` — —
- `connectionIndicator` — `ui/src/app/status.ts:15` — —
- `backendIndicator` — `ui/src/app/status.ts:43` — Состояние бэкенда, пока связи нет, — устаревшее: показываем «—», а не последнее известное.
- `blockedDetails` — `ui/src/app/status.ts:52` — Подсказка над счётчиком: кто и что написал; решение — за ведущим (`/пауза`, FR-31).
- `StatusBar.svelte` — `ui/src/app/StatusBar.svelte:1` — —

## ui/src/core
Публичный API core: фичи импортируют отсюда, а не из модулей пакета (R-63).

- `FrameScheduler` — `ui/src/core/batch.ts:8` — Запланировать вызов перед следующей отрисовкой; в окне — `requestAnimationFrame`.
- `animationFrame` — `ui/src/core/batch.ts:10` — —
- `FrameBatch` — `ui/src/core/batch.ts:20` — Очередь изменений до следующего кадра. Порядок сохраняется: смена связи и сообщения ядра идут
- `AudioSink` — `ui/src/core/client.ts:24` — —
- `CancelSink` — `ui/src/core/client.ts:26` — Звук хода надо оборвать: `turn` — отменённый ход, null — связь потеряна (сбросить всё).
- `CoreClientOptions` — `ui/src/core/client.ts:28` — —
- `CoreClient` — `ui/src/core/client.ts:37` — —
- `AUDIO_HEADER_SIZE` — `ui/src/core/frames.ts:11` — Заголовок аудиокадра `<BBHIQ`: тип, версия, seq, sample_rate, turn_id — docs/protocol.md.
- `MIC_HEADER_SIZE` — `ui/src/core/frames.ts:16` — Заголовок кадра микрофона `<BBHI`: тип, версия, seq, sample_rate.
- `encodeMicFrame` — `ui/src/core/frames.ts:20` — Кадр микрофона для ядра: заголовок + PCM s16le моно.
- `AudioFrame` — `ui/src/core/frames.ts:37` — Аудиокадр ядра. `turn` — в том же виде, что в JSON-сообщениях, чтобы их сопоставлять.
- `FrameError` — `ui/src/core/frames.ts:45` — Кадр не соответствует протоколу: ядро другой версии или повреждённые данные.
- `turnRef` — `ui/src/core/frames.ts:85` — Номер хода из аудиокадра в виде JSON-сообщений.
- `parseMessage` — `ui/src/core/frames.ts:109` — Текстовый кадр → сообщение ядра; `FrameError`, если это не сообщение протокола.
- `decodeAudioFrame` — `ui/src/core/frames.ts:126` — Бинарный кадр → аудиокадр. PCM не копируется: `Int16Array` смотрит в тот же буфер
- `FIRST_CHAR_SPAN` — `ui/src/core/probe.ts:8` — —
- `FirstCharProbe` — `ui/src/core/probe.ts:10` — —
- `FIRST_AUDIO_SPAN` — `ui/src/core/probe.ts:57` — —
- `FirstAudioProbe` — `ui/src/core/probe.ts:64` — Замер UI «реплика отправлена → звук ответа зазвучал» — настоящий TTFA (NFR-02: p50 ≤ 800 мс):
- `protocol.gen.ts` — `ui/src/core/protocol.gen.ts:1` — Автогенерация: `uv run python tools/gen_protocol.py`. Не редактировать.
- `int16ToFloat` — `ui/src/core/resample.ts:11` — Сэмплы s16 → float [-1, 1).
- `StreamResampler` — `ui/src/core/resample.ts:19` — —
- `startupMark` — `ui/src/core/startup.ts:7` — —
- `Role` — `ui/src/core/store.svelte.ts:29` — —
- `MessageStatus` — `ui/src/core/store.svelte.ts:30` — —
- `TurnPhase` — `ui/src/core/store.svelte.ts:32` — Фаза хода для аватара и кнопки «Стоп»: ждём первый токен / идёт ответ / ничего.
- `ChatMessage` — `ui/src/core/store.svelte.ts:34` — —
- `BranchesView` — `ui/src/core/store.svelte.ts:48` — —
- `PrivacyView` — `ui/src/core/store.svelte.ts:50` — —
- `SPAN_HISTORY` — `ui/src/core/store.svelte.ts:56` — —
- `SpeechProgress` — `ui/src/core/store.svelte.ts:59` — Что звучит в плеере (сообщает фича звука): ход, идёт ли звук, сыграно и получено, секунд.
- `VoiceState` — `ui/src/core/store.svelte.ts:70` — Голос в UI. Ход ядра заканчивается, когда синтез готов, а звучит голос дольше (синтез
- `AppStore` — `ui/src/core/store.svelte.ts:75` — —
- `CLOSE_REPLACED` — `ui/src/core/transport.ts:10` — Код закрытия «вытеснен новым клиентом» — `gateway/server.py` (ADR-0008).
- `SocketLike` — `ui/src/core/transport.ts:14` — Часть WebSocket, нужная транспорту: в тестах подменяется фейком.
- `SocketFactory` — `ui/src/core/transport.ts:24` — —
- `ConnectionState` — `ui/src/core/transport.ts:27` — `replaced` — ядро приняло другое окно; переподключаться нельзя, иначе окна вытесняют друг друга.
- `TransportListener` — `ui/src/core/transport.ts:29` — —
- `Backoff` — `ui/src/core/transport.ts:37` — Пауза перед попыткой n (с нуля): `min(maxMs, initialMs · factor^n)`.
- `TransportOptions` — `ui/src/core/transport.ts:43` — —
- `Transport` — `ui/src/core/transport.ts:66` — —
- `APP_VERSION` — `ui/src/core/version.ts:2` — Версия сборки для показа в окнах: номер, коммит и время запуска (vite.config.ts).

## ui/src/core/i18n
Тексты интерфейса по языкам издания (Этап 20): фичи берут `locale.t`, а не строки в разметке.

- `en` — `ui/src/core/i18n/en.ts:4` — —
- `Lang` — `ui/src/core/i18n/locale.svelte.ts:8` — —
- `isLang` — `ui/src/core/i18n/locale.svelte.ts:12` — —
- `locale` — `ui/src/core/i18n/locale.svelte.ts:32` — Один на приложение: язык — свойство издания, а не отдельной панели.
- `messagesFor` — `ui/src/core/i18n/locale.svelte.ts:35` — Словарь языка без реактивности — для тестов и чистых функций.
- `ru` — `ui/src/core/i18n/ru.ts:21` — —
- `Messages` — `ui/src/core/i18n/ru.ts:593` — —

## ui/src/features/ambient
Публичный API звука компьютера для сферы (Этап 22, R-63).

- `AmbientControl.svelte` — `ui/src/features/ambient/AmbientControl.svelte:1` — Включатель «сфера слышит звук компьютера» в строке статуса (Этап 22, ADR-0039).
- `AmbientBands` — `ui/src/features/ambient/systemAudio.ts:8` — —
- `SILENCE` — `ui/src/features/ambient/systemAudio.ts:14` — —
- `shape` — `ui/src/features/ambient/systemAudio.ts:22` — —
- `SystemAudio` — `ui/src/features/ambient/systemAudio.ts:38` — Слушатель звука компьютера; вне Tauri (Vite в браузере) недоступен.
- `readAmbientEnabled` — `ui/src/features/ambient/systemAudio.ts:76` — —
- `writeAmbientEnabled` — `ui/src/features/ambient/systemAudio.ts:84` — —

## ui/src/features/audio
Публичный API фичи звука: плеер голоса и его подключение к ядру (ADR-0003).

- `PlayerEvent` — `ui/src/features/audio/events.ts:3` — —
- `isPlayerEvent` — `ui/src/features/audio/events.ts:8` — —
- `connectVoice` — `ui/src/features/audio/index.ts:12` — Плеер, подключённый к клиенту ядра: кадры звука → плеер, отмена хода → сброс, начало звука →
- `LipsyncConfig` — `ui/src/features/audio/lipsync.ts:7` — —
- `DEFAULT_LIPSYNC` — `ui/src/features/audio/lipsync.ts:19` — Замер S-7.6 на Silero (48 кГц): пик RMS речи ~0.31, паузы между фразами ниже порога.
- `rms` — `ui/src/features/audio/lipsync.ts:27` — Среднеквадратичная громкость блока сэмплов.
- `MouthFollower` — `ui/src/features/audio/lipsync.ts:38` — —
- `FADE_SAMPLES` — `ui/src/features/audio/pcm-queue.ts:12` — Длина нарастания и затухания, сэмплов: ~3 мс — неслышно как «ступенька», щелчка нет.
- `PcmQueue` — `ui/src/features/audio/pcm-queue.ts:58` — —
- `PROCESSOR_NAME` — `ui/src/features/audio/player.worklet.ts:10` — —
- `PlayerCommand` — `ui/src/features/audio/player.worklet.ts:14` — —
- `MouthShape` — `ui/src/features/audio/viseme.ts:23` — —
- `NEUTRAL_SHAPE` — `ui/src/features/audio/viseme.ts:30` — —
- `mouthShape` — `ui/src/features/audio/viseme.ts:46` — Спектр в дБ (`getFloatFrequencyData`) → форма рта; пустой спектр — откат к громкости.
- `FormFollower` — `ui/src/features/audio/viseme.ts:65` — —
- `VoicePlayer` — `ui/src/features/audio/VoicePlayer.ts:24` — —

## ui/src/features/avatar
Публичный API фичи персонажа: сцена, контракт рендера и выбор вида (Этап 23).

- `AvatarReaction` — `ui/src/features/avatar/AvatarRenderer.ts:16` — Реакция на ход разговора, не зависящая от текста: «слушаю» (пользователь печатает),
- `StageSize` — `ui/src/features/avatar/AvatarRenderer.ts:19` — Размер области сцены в CSS-пикселях; рендер сам учитывает devicePixelRatio.
- `AvatarRenderer` — `ui/src/features/avatar/AvatarRenderer.ts:24` — —
- `AvatarStage.svelte` — `ui/src/features/avatar/AvatarStage.svelte:1` — —
- `StageRect` — `ui/src/features/avatar/gaze.ts:3` — —
- `gazeAt` — `ui/src/features/avatar/gaze.ts:14` — -1…1 по осям, y вверх (как `AvatarRenderer.lookAt`). За пределами сцены значение обрезается:
- `HeadAxis` — `ui/src/features/avatar/gesture.ts:6` — —
- `GestureSpec` — `ui/src/features/avatar/gesture.ts:8` — —
- `gestureAngle` — `ui/src/features/avatar/gesture.ts:18` — Добавка к углу головы через `elapsedMs`; огибающая возвращает голову на место к концу жеста.
- `MAX_DELTA_MS` — `ui/src/features/avatar/loop.ts:7` — Шаг после паузы или подвисания ограничен: иначе физика волос «выстрелит» за один кадр.
- `FrameSource` — `ui/src/features/avatar/loop.ts:10` — Источник кадров: в окне — `requestAnimationFrame`, в тестах — ручной.
- `Visibility` — `ui/src/features/avatar/loop.ts:16` — Видимость окна: `onChange` возвращает функцию отписки.
- `browserFrames` — `ui/src/features/avatar/loop.ts:21` — —
- `browserVisibility` — `ui/src/features/avatar/loop.ts:28` — —
- `AvatarLoop` — `ui/src/features/avatar/loop.ts:38` — —
- `MoodConfig` — `ui/src/features/avatar/mood.ts:8` — —
- `DEFAULT_MOOD` — `ui/src/features/avatar/mood.ts:16` — Пара фраз тишины — эмоция ещё «про» ответ; дольше — лицо застывает маской.
- `MoodFrame` — `ui/src/features/avatar/mood.ts:18` — —
- `Mood` — `ui/src/features/avatar/mood.ts:24` — —
- `NOD_MS` — `ui/src/features/avatar/nod.ts:8` — Длительность кивка, мс: короче — дёрганье, дольше — поклон.
- `NOD_DEGREES` — `ui/src/features/avatar/nod.ts:10` — Глубина кивка, градусы параметра `ParamAngleY` (диапазон модели обычно ±30).
- `nodAngle` — `ui/src/features/avatar/nod.ts:13` — Добавка к наклону головы через `elapsedMs` после начала кивка; вне кивка — 0.
- `THINKING_AFTER_MS` — `ui/src/features/avatar/reactions.ts:9` — Порог «думаю», мс: бюджет TTFA (NFR-02) — ответ медленнее нормы виден по лицу.
- `ConversationView` — `ui/src/features/avatar/reactions.ts:11` — —
- `isWaiting` — `ui/src/features/avatar/reactions.ts:23` — Реплика ушла, а ответа ещё не слышно (без голоса — не видно).
- `AmbientSource` — `ui/src/features/avatar/session.ts:13` — Полосы звука компьютера 0…1 (Этап 22).
- `MouthSource` — `ui/src/features/avatar/session.ts:17` — Открытие рта 0…1 за прошедшие `deltaMs`; без звука — всегда 0.
- `ActivitySource` — `ui/src/features/avatar/session.ts:19` — Идёт ли разговор (ход или голос): пока да — эмоция не угасает.
- `AvatarStatus` — `ui/src/features/avatar/session.ts:21` — —
- `RendererFactory` — `ui/src/features/avatar/session.ts:25` — Создатель рендера: вид показа в окне, фейк в тестах.
- `AvatarSession` — `ui/src/features/avatar/session.ts:31` — —
- `AvatarView` — `ui/src/features/avatar/view.ts:5` — Вид показа персонажа справа (Этап 23): окно персонажа с картинкой или сфера. Выбор — в меню по
- `AVATAR_VIEWS` — `ui/src/features/avatar/view.ts:7` — —
- `DEFAULT_VIEW` — `ui/src/features/avatar/view.ts:8` — —
- `parseView` — `ui/src/features/avatar/view.ts:12` — —
- `loadView` — `ui/src/features/avatar/view.ts:17` — Сохранённый вид; хранилище недоступно — вид по умолчанию.
- `saveView` — `ui/src/features/avatar/view.ts:25` — —

## ui/src/features/avatar/orb
—

- `Sphere` — `ui/src/features/avatar/orb/geometry.ts:6` — —
- `fibonacciSphere` — `ui/src/features/avatar/orb/geometry.ts:16` — `count` точек, равномерно по сфере (спираль Фибоначчи).
- `nearestEdges` — `ui/src/features/avatar/orb/geometry.ts:30` — Рёбра к `neighbors` ближайшим точкам; повторы (a–b и b–a) убираются.
- `buildSphere` — `ui/src/features/avatar/orb/geometry.ts:63` — —
- `ripple` — `ui/src/features/avatar/orb/geometry.ts:72` — Отклонение точки вдоль радиуса: «вибрация» голосом. Волны бегут по поверхности (зависят от
- `OrbRenderer` — `ui/src/features/avatar/orb/OrbRenderer.ts:25` — —
- `EMOTION_HUE` — `ui/src/features/avatar/orb/palette.ts:8` — Оттенок (0…360) эмоции; нейтральная — голубой «Джарвиса».
- `shimmerHue` — `ui/src/features/avatar/orb/palette.ts:19` — Переливание: медленный дрейф ±25° вокруг оттенка эмоции.
- `mixHue` — `ui/src/features/avatar/orb/palette.ts:24` — Плавный переход оттенка по короткой дуге круга; `t` 0…1.
- `sparkle` — `ui/src/features/avatar/orb/palette.ts:30` — Искрение точки: у каждой своя фаза, яркость 0.55…1.

## ui/src/features/avatar/portrait
—

- `CharacterControls.svelte` — `ui/src/features/avatar/portrait/CharacterControls.svelte:1` — —
- `HEAD_FRAMES` — `ui/src/features/avatar/portrait/head.ts:21` — —
- `HeadState` — `ui/src/features/avatar/portrait/head.ts:31` — —
- `headFrame` — `ui/src/features/avatar/portrait/head.ts:41` — —
- `PICTURE_TYPES` — `ui/src/features/avatar/portrait/picture.ts:8` — Форматы, которые `<img>` WebView2 показывает сам, включая анимированные GIF, WebP и APNG.
- `MAX_PICTURE_BYTES` — `ui/src/features/avatar/portrait/picture.ts:15` — —
- `PictureFit` — `ui/src/features/avatar/portrait/picture.ts:18` — Целиком, заполнить окошко или «мордашка в углу» (по умолчанию, просьба пользователя 2026-11-17).
- `pictureProblem` — `ui/src/features/avatar/portrait/picture.ts:21` — Причина отказа на языке интерфейса или `null`, если файл подходит.
- `parseFit` — `ui/src/features/avatar/portrait/picture.ts:32` — Способ вписать картинку: битое, чужое или не выбранное — «мордашка в углу».
- `loadFit` — `ui/src/features/avatar/portrait/picture.ts:38` — —
- `saveFit` — `ui/src/features/avatar/portrait/picture.ts:46` — —
- `windowStorage` — `ui/src/features/avatar/portrait/picture.ts:56` — localStorage окна; недоступно (приватный режим WebView) — без хранилища.
- `run` — `ui/src/features/avatar/portrait/picture.ts:84` — Запрос к хранилищу картинок (окошко, позы спутника); соединение закрывается после него.
- `loadPicture` — `ui/src/features/avatar/portrait/picture.ts:105` — Сохранённая картинка; нет её или хранилище недоступно — `null` (стандартный силуэт).
- `savePicture` — `ui/src/features/avatar/portrait/picture.ts:114` — —
- `clearPicture` — `ui/src/features/avatar/portrait/picture.ts:119` — —
- `pictureChanged` — `ui/src/features/avatar/portrait/picture.ts:125` — Картинку сменили: рендер окошка перечитывает её без перезапуска сцены.
- `characterChannel` — `ui/src/features/avatar/portrait/picture.ts:128` — Между окнами (главное и спутник): одно происхождение — общий канал.
- `portraitPose` — `ui/src/features/avatar/portrait/PortraitRenderer.ts:35` — Поза кадра: чистая функция времени и состояния — проверяется тестами.
- `PortraitRenderer` — `ui/src/features/avatar/portrait/PortraitRenderer.ts:52` — —

## ui/src/features/chat
Публичный API фичи чата: приложение монтирует только панель (R-63).

- `BranchBar.svelte` — `ui/src/features/chat/BranchBar.svelte:1` — —
- `Chat.svelte` — `ui/src/features/chat/Chat.svelte:1` — —
- `CommandHints.svelte` — `ui/src/features/chat/CommandHints.svelte:1` — Подсказки команд над полем ввода: что можно написать после «/». Щелчок или Enter — выполнить.
- `CommandId` — `ui/src/features/chat/commands.ts:6` — —
- `Command` — `ui/src/features/chat/commands.ts:8` — —
- `suggest` — `ui/src/features/chat/commands.ts:16` — Подсказки к набранному: только пока в поле одно «/слово» без пробела.
- `commandOf` — `ui/src/features/chat/commands.ts:24` — Команда, которую набрали целиком (`/private`), или null — обычная реплика.
- `Composer.svelte` — `ui/src/features/chat/Composer.svelte:1` — —
- `MAX_IMAGE_SIDE` — `ui/src/features/chat/image.ts:8` — Больше длинной стороны модели всё равно не увидят: проектор сжимает картинку сам.
- `ImageSize` — `ui/src/features/chat/image.ts:12` — —
- `Attachment` — `ui/src/features/chat/image.ts:17` — —
- `fitSize` — `ui/src/features/chat/image.ts:24` — Размер, в который картинка вписывается целиком; меньшая не растягивается.
- `encodeFrame` — `ui/src/features/chat/image.ts:33` — Кадр (файл или снимок) → JPEG в base64. Ошибка — у вызывающего: показать, что не вышло.
- `attachmentFromFile` — `ui/src/features/chat/image.ts:50` — —
- `isSendKey` — `ui/src/features/chat/keys.ts:6` — Enter во время набора через IME (выбор иероглифа и т. п.) подтверждает ввод, а не отправляет.
- `isStopKey` — `ui/src/features/chat/keys.ts:10` — —
- `ESTIMATED_HEIGHT` — `ui/src/features/chat/layout.ts:8` — Оценка высоты не измеренного сообщения, px: реплика в 2–3 строки с отступами.
- `OVERSCAN_PX` — `ui/src/features/chat/layout.ts:10` — Запас над и под экраном, px: быстрая прокрутка не показывает пустоту до догрузки.
- `STICK_TOLERANCE_PX` — `ui/src/features/chat/layout.ts:12` — Насколько можно не докрутить до низа, чтобы список всё ещё «прилипал» к новым сообщениям.
- `Viewport` — `ui/src/features/chat/layout.ts:14` — —
- `Placed` — `ui/src/features/chat/layout.ts:19` — —
- `ListWindow` — `ui/src/features/chat/layout.ts:24` — —
- `computeWindow` — `ui/src/features/chat/layout.ts:56` — —
- `isAtBottom` — `ui/src/features/chat/layout.ts:76` — Пользователь внизу списка — новые сообщения прокручивают к себе; ушёл читать выше — нет.
- `MeasureTarget` — `ui/src/features/chat/measure.ts:7` — —
- `measureHeight` — `ui/src/features/chat/measure.ts:27` — —
- `MessageList.svelte` — `ui/src/features/chat/MessageList.svelte:1` — —
- `asksForScreen` — `ui/src/features/chat/screen.ts:14` — Просит ли реплика посмотреть на экран; решает только открыть диалог, снимка без него нет.
- `wantsCapture` — `ui/src/features/chat/screen.ts:19` — Открыть ли диалог вместо отправки: снимок уже есть — значит, пользователь решает его судьбу.
- `Stoppable` — `ui/src/features/chat/screen.ts:24` — Что нужно от потока: остановить его.
- `ScreenSource` — `ui/src/features/chat/screen.ts:29` — Что нужно от захвата: в тестах — подмена.
- `captureFrom` — `ui/src/features/chat/screen.ts:53` — Снимок выбранного окна; null — пользователь передумал. Захват завершается при любом исходе, чтобы
- `captureScreen` — `ui/src/features/chat/screen.ts:73` — —
- `SPEECH_CHARS_PER_S` — `ui/src/features/chat/subtitles.ts:10` — Темп речи до конца хода, символов на секунду звука: Silero `xenia` — ≈ 18 (замер S-7.6).
- `SUBTITLES_KEY` — `ui/src/features/chat/subtitles.ts:12` — Ключ настройки в localStorage.
- `SettingStorage` — `ui/src/features/chat/subtitles.ts:15` — Нужное от localStorage: в тестах — словарь.
- `SubtitleView` — `ui/src/features/chat/subtitles.ts:17` — —
- `revealedLength` — `ui/src/features/chat/subtitles.ts:24` — Сколько символов сообщения показать; null — всё сообщение (не субтитр).
- `Subtitles` — `ui/src/features/chat/subtitles.ts:46` — Текст сообщений в режиме субтитров; помнит показанное, чтобы оно не убывало.
- `readSubtitles` — `ui/src/features/chat/subtitles.ts:63` — Настройка из хранилища; недоступное хранилище (политика WebView) — режим выключен.
- `writeSubtitles` — `ui/src/features/chat/subtitles.ts:71` — —
- `TYPING_DEBOUNCE_MS` — `ui/src/features/chat/typing.ts:8` — Пауза в наборе, после которой черновик уходит ядру, мс (T-05: ~300).
- `Timers` — `ui/src/features/chat/typing.ts:10` — —
- `TypingDebouncer` — `ui/src/features/chat/typing.ts:22` — —

## ui/src/features/chats
Публичный API панели чатов (Этап 21, R-63).

- `ChatSidebar.svelte` — `ui/src/features/chats/ChatSidebar.svelte:1` — Чаты слева, как в Claude (Этап 21, ADR-0037): у каждого чата своя память и свой контекст,
- `ChatGroup` — `ui/src/features/chats/groups.ts:7` — —
- `groupChats` — `ui/src/features/chats/groups.ts:14` — Без категории — сверху, затем категории в порядке создания; пустые категории тоже видны.
- `chatLabel` — `ui/src/features/chats/groups.ts:30` — Название в списке: пустое — «Новый чат» на языке интерфейса.
- `SettingStorage` — `ui/src/features/chats/groups.ts:34` — —
- `readCollapsed` — `ui/src/features/chats/groups.ts:42` — Свёрнута ли панель чатов; хранилище недоступно — развёрнута.
- `writeCollapsed` — `ui/src/features/chats/groups.ts:50` — —

## ui/src/features/companion
Публичный API «Сопровождения» (Этап 23, ADR-0045; R-63).

- `ChecklistButton.svelte` — `ui/src/features/companion/ChecklistButton.svelte:1` — Кнопка чек-листа у персонажа в главном окне (просьба пользователя 2026-11-18): строки присылает слой
- `Companion.svelte` — `ui/src/features/companion/Companion.svelte:1` — —
- `CompanionMenu.svelte` — `ui/src/features/companion/CompanionMenu.svelte:1` — —
- `CompanionReturn.svelte` — `ui/src/features/companion/CompanionReturn.svelte:1` — —
- `DeskKeepsakes.svelte` — `ui/src/features/companion/DeskKeepsakes.svelte:1` — —
- `startFeed` — `ui/src/features/companion/feed.ts:17` — Запустить передачу; `mouth(dt)` — громкость голоса 0…1. Возвращает остановку.
- `createDesk` — `ui/src/features/companion/keepsakeScene.svelte.ts:16` — —
- `CompanionWhen` — `ui/src/features/companion/settings.ts:5` — Настройки «Сопровождения» (Этап 23, ADR-0045): общие для главного окна и слоя спутника через
- `CompanionBehavior` — `ui/src/features/companion/settings.ts:6` — —
- `CompanionSettings` — `ui/src/features/companion/settings.ts:8` — —
- `DESKTOP_REACTIONS` — `ui/src/features/companion/settings.ts:20` — —
- `KEEPSAKE_TIMING` — `ui/src/features/companion/settings.ts:33` — —
- `COMPANION_KEY` — `ui/src/features/companion/settings.ts:53` — —
- `DIVERSION` — `ui/src/features/companion/settings.ts:54` — —
- `TOUCH` — `ui/src/features/companion/settings.ts:62` — —
- `HEIGHTS` — `ui/src/features/companion/settings.ts:70` — —
- `DEFAULT_SETTINGS` — `ui/src/features/companion/settings.ts:71` — —
- `parseSettings` — `ui/src/features/companion/settings.ts:84` — Разбор сохранённого: чужое или битое — умолчания.
- `loadSettings` — `ui/src/features/companion/settings.ts:111` — —
- `saveSettings` — `ui/src/features/companion/settings.ts:119` — —
- `shouldShow` — `ui/src/features/companion/settings.ts:131` — Виден ли спутник. Полный экран его больше не прячет (просьба пользователя 2026-11-17: виден всегда, в

## ui/src/features/companion/behavior
Подпакет «behavior» спутника: импорт снаружи — только через этот файл (R-06).

- `Bond` — `ui/src/features/companion/behavior/bond.ts:6` — Привязанность спутника к пользователю (COMPANION.md, этап 3): поглаживания, разговоры и проведённое
- `BondEvent` — `ui/src/features/companion/behavior/bond.ts:13` — —
- `BondTone` — `ui/src/features/companion/behavior/bond.ts:14` — —
- `BOND_KEY` — `ui/src/features/companion/behavior/bond.ts:16` — —
- `settle` — `ui/src/features/companion/behavior/bond.ts:22` — Забывание: без внимания привязанность тает к стартовой с полураспадом в неделю.
- `grow` — `ui/src/features/companion/behavior/bond.ts:28` — Событие внимания: чем выше привязанность, тем медленнее она растёт дальше.
- `bondTone` — `ui/src/features/companion/behavior/bond.ts:33` — —
- `parseBond` — `ui/src/features/companion/behavior/bond.ts:39` — —
- `createBuilding` — `ui/src/features/companion/behavior/building.svelte.ts:4` — —
- `createNote` — `ui/src/features/companion/behavior/deskNote.svelte.ts:5` — —
- `DesktopEvent` — `ui/src/features/companion/behavior/desktopEvents.ts:14` — —
- `DesktopReactions` — `ui/src/features/companion/behavior/desktopEvents.ts:19` — —
- `Diversion` — `ui/src/features/companion/behavior/diversions.ts:3` — —
- `Scene` — `ui/src/features/companion/behavior/diversions.ts:4` — —
- `Diversions` — `ui/src/features/companion/behavior/diversions.ts:10` — —
- `Habit` — `ui/src/features/companion/behavior/habits.ts:8` — —
- `AppWatch` — `ui/src/features/companion/behavior/habits.ts:25` — —
- `FAVORITES_KEY` — `ui/src/features/companion/behavior/habits.ts:67` — —
- `pickIcon` — `ui/src/features/companion/behavior/habits.ts:70` — Значок, на который садиться: чаще тот, где чаще гладили (вес 1 + число поглаживаний).
- `isRecycleBin` — `ui/src/features/companion/behavior/habits.ts:84` — —
- `parseFavorites` — `ui/src/features/companion/behavior/habits.ts:88` — —
- `Keepsake` — `ui/src/features/companion/behavior/keepsakes.ts:1` — —
- `Workday` — `ui/src/features/companion/behavior/keepsakes.ts:5` — —
- `parsePocket` — `ui/src/features/companion/behavior/keepsakes.ts:26` — —
- `addItem` — `ui/src/features/companion/behavior/keepsakes.ts:35` — —
- `dayProgress` — `ui/src/features/companion/behavior/keepsakes.ts:39` — —
- `Life` — `ui/src/features/companion/behavior/life.ts:34` — —
- `Mood` — `ui/src/features/companion/behavior/mood.ts:6` — Настроение спутника (BEHAVIOR §2): бодрость и радость 0…1. Меняются медленно, определяют, когда он
- `MoodEvent` — `ui/src/features/companion/behavior/mood.ts:13` — —
- `MoodTone` — `ui/src/features/companion/behavior/mood.ts:14` — —
- `MOOD_KEY` — `ui/src/features/companion/behavior/mood.ts:16` — —
- `neutralMood` — `ui/src/features/companion/behavior/mood.ts:33` — —
- `nudge` — `ui/src/features/companion/behavior/mood.ts:38` — Событие сдвигает настроение.
- `drift` — `ui/src/features/companion/behavior/mood.ts:47` — Течение времени (`dt` секунд): ночью бодрость падает, утром растёт; долгий простой тянет радость вниз,
- `tone` — `ui/src/features/companion/behavior/mood.ts:57` — —
- `restTimes` — `ui/src/features/companion/behavior/mood.ts:63` — Через сколько секунд простоя ложится и засыпает: устал — раньше.
- `pace` — `ui/src/features/companion/behavior/mood.ts:70` — Множитель пауз между прогулками: бодрый гуляет чаще.
- `parseMood` — `ui/src/features/companion/behavior/mood.ts:75` — Сохранённое настроение; за ночь (8 ч) — к середине.
- `loadMood` — `ui/src/features/companion/behavior/mood.ts:98` — —
- `saveMood` — `ui/src/features/companion/behavior/mood.ts:106` — —
- `Reactions` — `ui/src/features/companion/behavior/reactions.ts:23` — —

## ui/src/features/companion/body
Подпакет «body» спутника: импорт снаружи — только через этот файл (R-06).

- `WALK_LIMIT` — `ui/src/features/companion/body/brain.ts:28` — Ближе — пешком или прыжком, дальше — молнией (решение пользователя, раздел 9.1).
- `Brain` — `ui/src/features/companion/body/brain.ts:49` — —
- `PoseState` — `ui/src/features/companion/body/pose.ts:8` — —
- `poseOf` — `ui/src/features/companion/body/pose.ts:50` — —
- `Phase` — `ui/src/features/companion/body/types.ts:4` — —
- `Music` — `ui/src/features/companion/body/types.ts:18` — Радио (BEHAVIOR §8): играет — поёт стоя и не гуляет; пауза — слушает в наушниках.
- `Effect` — `ui/src/features/companion/body/types.ts:20` — —
- `Body` — `ui/src/features/companion/body/types.ts:31` — —

## ui/src/features/companion/controller
Подпакет «controller» спутника: контроллер и его части; импорт снаружи — только через этот файл (R-06).

- `Feed` — `ui/src/features/companion/controller/assistantFeed.ts:8` — Подача главного окна (`companion-feed`, ADR-0045, ADR-0049).
- `AssistantFeed` — `ui/src/features/companion/controller/assistantFeed.ts:23` — —
- `Speak` — `ui/src/features/companion/controller/conductor.ts:18` — Предложить фразу голосу; `watchLine` — фраза самого просмотра (пропускается и во время фильма).
- `ConductorParts` — `ui/src/features/companion/controller/conductor.ts:20` — —
- `Situation` — `ui/src/features/companion/controller/conductor.ts:30` — Что от контроллера нужно для картины кадра.
- `Conductor` — `ui/src/features/companion/controller/conductor.ts:45` — —
- `CompanionController` — `ui/src/features/companion/controller/controller.ts:22` — —
- `CursorInput` — `ui/src/features/companion/controller/cursorInput.ts:7` — —
- `EscortState` — `ui/src/features/companion/controller/escort.ts:17` — —
- `Escort` — `ui/src/features/companion/controller/escort.ts:24` — —
- `CompanionFrame` — `ui/src/features/companion/controller/frame.ts:12` — —
- `Gesture` — `ui/src/features/companion/controller/gestures.ts:11` — —
- `GestureHooks` — `ui/src/features/companion/controller/gestures.ts:19` — —
- `Gestures` — `ui/src/features/companion/controller/gestures.ts:28` — —
- `pickOne` — `ui/src/features/companion/controller/pickOne.ts:1` — —
- `pointerHandlers` — `ui/src/features/companion/controller/pointer.ts:2` — —
- `Ports` — `ui/src/features/companion/controller/ports.ts:10` — —
- `tauriPorts` — `ui/src/features/companion/controller/ports.ts:30` — —
- `MainState` — `ui/src/features/companion/controller/presence.ts:10` — Главное окно: показано ли и в фокусе, где стоит (физические пиксели).
- `Presence` — `ui/src/features/companion/controller/presence.ts:16` — —
- `MediaChange` — `ui/src/features/companion/controller/scout.ts:27` — Смена состояния того, что играет: для реплик «пауза» / «продолжаем».
- `Scout` — `ui/src/features/companion/controller/scout.ts:29` — —
- `Speech` — `ui/src/features/companion/controller/speech.ts:12` — —
- `subscribe` — `ui/src/features/companion/controller/subscriptions.ts:8` — —
- `createView` — `ui/src/features/companion/controller/view.svelte.ts:27` — —
- `CompanionView` — `ui/src/features/companion/controller/view.svelte.ts:284` — —

## ui/src/features/companion/look
Подпакет «look» спутника: импорт снаружи — только через этот файл (R-06).

- `Checklist.svelte` — `ui/src/features/companion/look/Checklist.svelte:1` — —
- `CheckRow` — `ui/src/features/companion/look/checklist.ts:10` — —
- `Checklist` — `ui/src/features/companion/look/checklist.ts:23` — —
- `checklist` — `ui/src/features/companion/look/checklist.ts:127` — Строки чек-листа на момент `now` (мс, `performance.now()`).
- `serveChecklist` — `ui/src/features/companion/look/checklistLink.ts:40` — Слой спутника: отвечать строками чек-листа, пока главное окно просит. Вернёт отписку.
- `watchChecklist` — `ui/src/features/companion/look/checklistLink.ts:58` — Главное окно: просить строки и получать их в `onRows`. Вернёт отписку (перестать просить).
- `CompanionMenu.svelte` — `ui/src/features/companion/look/CompanionMenu.svelte:1` — —
- `poseScene` — `ui/src/features/companion/look/diversions.ts:16` — —
- `drawDiversion` — `ui/src/features/companion/look/diversions.ts:26` — Props are painted in unit coordinates relative to the boots.
- `Point` — `ui/src/features/companion/look/effects.ts:8` — —
- `Random` — `ui/src/features/companion/look/effects.ts:9` — —
- `seeded` — `ui/src/features/companion/look/effects.ts:12` — Генератор с зерном (mulberry32): молния не «дёргается» сильнее, чем мы просим.
- `lightning` — `ui/src/features/companion/look/effects.ts:24` — Ломаная молнии смещением средней точки: `depth` уровней, отклонение — доля длины отрезка.
- `branches` — `ui/src/features/companion/look/effects.ts:50` — Ответвления: короткие молнии от случайных точек ствола.
- `along` — `ui/src/features/companion/look/effects.ts:63` — Точка на ломаной на доле `t` её длины — где сейчас разряд.
- `drawBolt` — `ui/src/features/companion/look/effects.ts:97` — Молния тремя проходами: широкое свечение, мягкая линия, яркая сердцевина.
- `drawEffects` — `ui/src/features/companion/look/effects.ts:277` — Нарисовать эффекты тела; `seed` меняется 30 раз в секунду — молния «живёт».
- `Inspection.svelte` — `ui/src/features/companion/look/Inspection.svelte:1` — —
- `MenuPlace` — `ui/src/features/companion/look/menu.ts:7` — —
- `placeMenu` — `ui/src/features/companion/look/menu.ts:20` — Левый верхний угол меню размера `size` для щелчка в `at` на экране `view`.
- `SOFT_LOOPS` — `ui/src/features/companion/look/motion.ts:30` — Циклы, где кадры отличаются только телом: в них растворение уместно. Лицо меняется — резко. «Держат» и
- `Swap` — `ui/src/features/companion/look/motion.ts:44` — Этап смены позы: старая уходит (`out`) или новая приходит (`in`), `k` — 0…1.
- `Pose2D` — `ui/src/features/companion/look/motion.ts:49` — —
- `Motion` — `ui/src/features/companion/look/motion.ts:58` — —
- `FALLBACK` — `ui/src/features/companion/look/pack.ts:19` — Замены отсутствующей позы, в порядке предпочтения; всё кончается позой `stand`.
- `ANCHORS` — `ui/src/features/companion/look/pack.ts:49` — Точка опоры позы — доля ширины и высоты картинки: сиденье, ступни, ладони, «шиворот».
- `CANVAS_RATIO` — `ui/src/features/companion/look/pack.ts:81` — Холст позы 512×1024, рост персонажа ~960 (раздел 7.2): холст выше роста в 1024/960 раз.
- `LOOP_FPS` — `ui/src/features/companion/look/pack.ts:89` — Частота кадров зацикленной позы (`<поза>_1…N`), кадров в секунду.
- `FrameState` — `ui/src/features/companion/look/pack.ts:117` — Что сейчас с персонажем: для выбора кадра. `blink` — доля моргания 0…1 или `null`.
- `sequence` — `ui/src/features/companion/look/pack.ts:127` — Кадры `<имя>_1`, `<имя>_2` … подряд, пока есть.
- `pickFrame` — `ui/src/features/companion/look/pack.ts:171` — Кадр для позы с учётом замен: речь (кадры рта по громкости), моргание, зацикленные кадры позы,
- `poseName` — `ui/src/features/companion/look/pack.ts:179` — Имя позы из имени файла: `Sit_Edge.PNG` → `sit_edge`; не картинка — `null`.
- `savePoses` — `ui/src/features/companion/look/pack.ts:186` — Сохранить позы из выбранной папки; вернёт, сколько картинок принято.
- `clearPoses` — `ui/src/features/companion/look/pack.ts:198` — —
- `DEFAULT_PACK` — `ui/src/features/companion/look/pack.ts:209` — Встроенный персонаж (`ui/public/characters/default/`; подгонка — `docs/character/README.md`).
- `PACK_HEIGHT` — `ui/src/features/companion/look/pack.ts:219` — Высота кадра встроенного пакета; выше — место над головой (штамп, рожки), FRAMES-6 «Принято».
- `loadPoses` — `ui/src/features/companion/look/pack.ts:262` — Позы как `ImageBitmap`, уменьшенные до экранного размера (5.2: экономная загрузка): загруженные
- `RING` — `ui/src/features/companion/look/pack.ts:284` — Циклы с направлением (походка, лазанье, танец) — кольцом; спокойные — «туда-обратно» (ANIMATION.md).
- `loopIndex` — `ui/src/features/companion/look/pack.ts:297` — Номер кадра цикла. «Туда-обратно» (1-2-3-4-3-2): нет скачка с последнего кадра на первый, и из
- `PANEL` — `ui/src/features/companion/look/panel.ts:8` — Табло в долях кадра — измерено по сгенерированным кадрам `frames-4` (2026-11-18), с отступом внутрь.
- `panelRect` — `ui/src/features/companion/look/panel.ts:12` — Прямоугольник табло на экране по рамке нарисованного кадра.
- `drawPanel` — `ui/src/features/companion/look/panel.ts:22` — Написать `text` на табло; не влезает — медленно бежит по кругу (`time` — секунды).
- `placeholderPose` — `ui/src/features/companion/look/placeholder.ts:289` — Силуэт позы: широкие линии с градиентом палитры окна, круг головы, подпись с именем позы.
- `Placement` — `ui/src/features/companion/look/placement.ts:5` — Где рисовать кадр позы относительно точки опоры: размер и сдвиг центра. Кадр выше обычного (место над
- `placement` — `ui/src/features/companion/look/placement.ts:19` — `tall` — во сколько раз кадр выше обычного (1 — обычный); `ANCHORS` заданы в долях обычного кадра.
- `growsDown` — `ui/src/features/companion/look/placement.ts:33` — Опора в верхней половине кадра — лишнее место у высокого кадра снизу (подгонка FRAMES/этапов — так же).
- `tallness` — `ui/src/features/companion/look/placement.ts:38` — Во сколько раз кадр выше обычного; `unit` — высота обычного кадра (рост × CANVAS_RATIO).
- `RadioCard.svelte` — `ui/src/features/companion/look/RadioCard.svelte:1` — —
- `ScenePose` — `ui/src/features/companion/look/scenePoses.ts:7` — —
- `SCENE_FALLBACK` — `ui/src/features/companion/look/scenePoses.ts:30` — Без своих кадров (пакет пользователя) сцена рисуется той позой, что была до FRAMES-6.
- `SCENE_ANCHORS` — `ui/src/features/companion/look/scenePoses.ts:57` — —
- `SCENE_FPS` — `ui/src/features/companion/look/scenePoses.ts:82` — Кадров в секунду. У одноразовых сцен — так, чтобы кадры уложились в длительность сцены.
- `ONCE` — `ui/src/features/companion/look/scenePoses.ts:112` — Одноразовые сцены: кадры идут по разу от начала позы и держат последний, а не крутятся.
- `SCENE_RING` — `ui/src/features/companion/look/scenePoses.ts:129` — Циклы с направлением (бег, ноша) — кольцом, а не «туда-обратно».
- `onceFrames` — `ui/src/features/companion/look/scenePoses.ts:135` — Кадры одноразовой сцены по порядку: `<имя>_1…N`. Базовый кадр `<имя>` — копия одного из них (этапы
- `onceIndex` — `ui/src/features/companion/look/scenePoses.ts:141` — Номер кадра одноразовой сцены: `since` секунд от начала позы, последний кадр держится.
- `Look` — `ui/src/features/companion/look/stage.ts:47` — —
- `CompanionStage` — `ui/src/features/companion/look/stage.ts:60` — —

## ui/src/features/companion/mind
«Разум» спутника (MIND.md, ADR-0051): картина мира со сглаживанием, потребности, стимулы, арбитр

- `ActivityId` — `ui/src/features/companion/mind/activities.ts:8` — —
- `MindContext` — `ui/src/features/companion/mind/activities.ts:22` — Что арбитр знает о мире в момент оценки (сглаженное, MIND §3.1–3.3).
- `ACTIVITIES` — `ui/src/features/companion/mind/activities.ts:57` — —
- `Band` — `ui/src/features/companion/mind/arbiter.ts:6` — Арбитр действий (MIND §3.4): utility AI с защитой от метаний — группы важности, минимальная длительность,
- `Activity` — `ui/src/features/companion/mind/arbiter.ts:8` — —
- `Choice` — `ui/src/features/companion/mind/arbiter.ts:23` — —
- `Arbiter` — `ui/src/features/companion/mind/arbiter.ts:35` — —
- `clamp01` — `ui/src/features/companion/mind/curves.ts:2` — Кривые отклика utility AI (MIND §2, §4): вход 0…1 → оценка 0…1.
- `smoothstep` — `ui/src/features/companion/mind/curves.ts:7` — Сглаженная ступень между `from` и `to`: ниже — 0, выше — 1, между — плавно.
- `need` — `ui/src/features/companion/mind/curves.ts:13` — Потребность: до 0,4 почти не тянет, к 0,9 — тянет сильно.
- `Drive` — `ui/src/features/companion/mind/drives.ts:7` — —
- `DriveContext` — `ui/src/features/companion/mind/drives.ts:12` — —
- `Drives` — `ui/src/features/companion/mind/drives.ts:20` — —
- `Fact` — `ui/src/features/companion/mind/fact.ts:6` — Сглаженный факт картины мира (MIND §3.1): становится правдой, если сырой сигнал продержался
- `Ranked` — `ui/src/features/companion/mind/index.ts:16` — Строка чек-листа: баллы действия, можно ли начать (нет паузы) и идёт ли оно сейчас.
- `Senses` — `ui/src/features/companion/mind/index.ts:28` — Сырые наблюдения кадра: сглаживает их сам «Разум».
- `Mind` — `ui/src/features/companion/mind/index.ts:56` — —
- `Fix` — `ui/src/features/companion/mind/sanity.ts:7` — Сторож «Разума» (COMPANION.md, часть III): раз в секунду сверяет состояние тела и решений с правилами
- `Snapshot` — `ui/src/features/companion/mind/sanity.ts:10` — Что сторож видит в кадре.
- `Sanity` — `ui/src/features/companion/mind/sanity.ts:42` — —
- `Stimulus` — `ui/src/features/companion/mind/stimuli.ts:5` — Стимулы (MIND §3.3, «разрешители» Блумберга): событие не командует действием, а на время поднимает
- `Stimuli` — `ui/src/features/companion/mind/stimuli.ts:16` — —
- `VoiceKind` — `ui/src/features/companion/mind/voice.ts:7` — Голос спутника (MIND §3.5): все его фразы — через один регулятор. Прямые ответы (гладят, трясут) —
- `VoiceState` — `ui/src/features/companion/mind/voice.ts:22` — —
- `Voice` — `ui/src/features/companion/mind/voice.ts:29` — —

## ui/src/features/companion/phrases
Выбор фразы поглаживания (BEHAVIOR §7): раздел — по номеру клика в серии и по состоянию спутника,

- `watchPhrases` — `ui/src/features/companion/phrases/index.ts:14` — —
- `PetContext` — `ui/src/features/companion/phrases/index.ts:28` — —
- `petPhrases` — `ui/src/features/companion/phrases/index.ts:40` — —
- `petSection` — `ui/src/features/companion/phrases/index.ts:45` — Раздел для фразы или `null` — на этом клике молчит. Первое касание окрашено состоянием.
- `petLine` — `ui/src/features/companion/phrases/index.ts:59` — Фраза раздела без повтора недавних; `recent` дополняется сказанной.
- `PET_EN` — `ui/src/features/companion/phrases/pet.en.ts:4` — —
- `PET_RU` — `ui/src/features/companion/phrases/pet.ru.ts:4` — —
- `PetPhrases` — `ui/src/features/companion/phrases/types.ts:2` — Разделы фраз поглаживания (BEHAVIOR §7).
- `WatchPhrases` — `ui/src/features/companion/phrases/types.ts:26` — Фразы «смотрим вместе» (BEHAVIOR §11.2): универсальные, к любому фильму.
- `WATCH_EN` — `ui/src/features/companion/phrases/watch.en.ts:8` — —
- `WATCH_RU` — `ui/src/features/companion/phrases/watch.ru.ts:8` — —

## ui/src/features/companion/senses
Подпакет «senses» спутника: импорт снаружи — только через этот файл (R-06).

- `PlayWatch` — `ui/src/features/companion/senses/play.ts:19` — —
- `caught` — `ui/src/features/companion/senses/play.ts:40` — Курсор у самой груди — «поймал».
- `quotedNames` — `ui/src/features/companion/senses/pointer.ts:9` — Названия в кавычках «…», "…", “…” длиной 2–40 знаков.
- `findTarget` — `ui/src/features/companion/senses/pointer.ts:15` — Видимый элемент, название которого совпадает с одним из названий (без регистра): точное — лучше.
- `RemarkTopic` — `ui/src/features/companion/senses/remarks.ts:9` — —
- `topicOf` — `ui/src/features/companion/senses/remarks.ts:86` — —
- `TimeOfDay` — `ui/src/features/companion/senses/remarks.ts:91` — —
- `timeOfDay` — `ui/src/features/companion/senses/remarks.ts:93` — —
- `remark` — `ui/src/features/companion/senses/remarks.ts:109` — Комментарий: чаще — про программу, иногда — про время суток или простой; без повтора подряд.
- `nextPause` — `ui/src/features/companion/senses/remarks.ts:123` — Пауза до следующего комментария сам по себе, секунды: не часто, чтобы не надоедал.
- `Target` — `ui/src/features/companion/senses/remarks.ts:128` — Элемент экрана от оболочки (`companion_targets`, ADR-0048): кнопка, ссылка, вкладка, значок.
- `choosePoke` — `ui/src/features/companion/senses/remarks.ts:140` — Что потыкать: случайный элемент целиком на экране. Палец — к ближнему краю элемента, тело — с той
- `SiteTopic` — `ui/src/features/companion/senses/sites.ts:5` — Сайты в браузере (BEHAVIOR §5): тема — по названию вкладки, которое и так видно на экране (UI
- `siteOf` — `ui/src/features/companion/senses/sites.ts:36` — —
- `browserTopic` — `ui/src/features/companion/senses/sites.ts:48` — Что сказать про браузер по названиям вкладок: «много вкладок», тема узнанного сайта или `null` (тогда
- `CursorTouch` — `ui/src/features/companion/senses/stroking.ts:5` — One short trail in screen coordinates; only keep the latest turning point.
- `Trigger` — `ui/src/features/companion/senses/triggers.ts:6` — Триггеры спутника (BEHAVIOR §3): события мыши, окна-хозяина и времени → реакция с перезарядкой.
- `Cooldowns` — `ui/src/features/companion/senses/triggers.ts:34` — —
- `CursorWatch` — `ui/src/features/companion/senses/triggers.ts:55` — Курсор: возвращение после отсутствия (T7), «смотрит» (T8), рывок рядом (T9), долгая работа (T17).
- `shaken` — `ui/src/features/companion/senses/triggers.ts:96` — Трясут мышью (T4): за последнюю секунду три и больше разворота на скорости больше 1500 px/с.
- `dragged` — `ui/src/features/companion/senses/triggers.ts:116` — Окно-хозяина таскают быстро (T10): скорость сдвига больше 600 px/с.
- `lateNight` — `ui/src/features/companion/senses/triggers.ts:125` — Ночь (T16): с часа до пяти.
- `WatchContext` — `ui/src/features/companion/senses/watch.ts:24` — —
- `watching` — `ui/src/features/companion/senses/watch.ts:32` — —
- `Media` — `ui/src/features/companion/senses/watch.ts:39` — Что играет в системе (`companion_media`, ADR-0052).
- `loudMoment` — `ui/src/features/companion/senses/watch.ts:51` — Громкое место фильма (этап 5): пик заметно выше обычной громкости источника. `avg` — сглаженная
- `musicPlaying` — `ui/src/features/companion/senses/watch.ts:94` — Музыка играет в музыкальной программе (Spotify, Яндекс Музыка, AIMP…) — для «потанцевать».
- `PAUSE_KEEP_S` — `ui/src/features/companion/senses/watch.ts:101` — Пауза — часть просмотра: столько секунд на паузе он ещё «смотрит».
- `mediaVideo` — `ui/src/features/companion/senses/watch.ts:107` — Видео по сеансам мультимедиа Windows (ADR-0052): играет (или недавно встал на паузу) браузер или
- `pickMedia` — `ui/src/features/companion/senses/watch.ts:121` — Из всех источников звука (`companion_media`) — видео: играющее важнее стоящего на паузе; нет —
- `keepWatching` — `ui/src/features/companion/senses/watch.ts:133` — Начать смотреть — видео в фокусе или на весь экран; уже смотрим — держимся, пока фильм идёт или стоит

## ui/src/features/companion/space
Подпакет «space» спутника: импорт снаружи — только через этот файл (R-06).

- `Pose` — `ui/src/features/companion/space/anchors.ts:7` — —
- `Surface` — `ui/src/features/companion/space/anchors.ts:70` — Опора: горизонтальная (край окна, «пол») или вертикальная (бок окна).
- `Spot` — `ui/src/features/companion/space/anchors.ts:78` — Место на опоре: точка опоры позы (сиденье, ступни, ладони) и сама поза.
- `SCREEN` — `ui/src/features/companion/space/anchors.ts:88` — «Хозяин» боков экрана: не окно, за ним не следят и его не опрашивают.
- `SNAP_RADIUS` — `ui/src/features/companion/space/anchors.ts:95` — —
- `surfaces` — `ui/src/features/companion/space/anchors.ts:100` — Все опоры картины: открытые участки верхних краёв окон, бока окон, «пол» над панелью задач.
- `spotOn` — `ui/src/features/companion/space/anchors.ts:140` — Место на опоре `surface`, ближайшее к точке; поза — по месту.
- `hostId` — `ui/src/features/companion/space/anchors.ts:167` — Окно, на котором место (за ним следят), или `null` — «пол», верх и бока экрана.
- `ICONS` — `ui/src/features/companion/space/anchors.ts:174` — «Хозяин» значков рабочего стола: они опоры, но не окна (оболочка их не отслеживает).
- `iconSurfaces` — `ui/src/features/companion/space/anchors.ts:177` — Верх значков рабочего стола как опоры (по образцу Capri): сесть на «Корзину» или «Steam».
- `wallX` — `ui/src/features/companion/space/anchors.ts:190` — Где стоит персонаж у бока: на полкорпуса от стены, внутри экрана и вне окна.
- `snap` — `ui/src/features/companion/space/anchors.ts:206` — Ближайшее место в радиусе `radius` или `null` — тогда спутник «парит» и опускается сам.
- `below` — `ui/src/features/companion/space/anchors.ts:225` — Горизонтальная опора под точкой (падение): ближайшая сверху вниз, иначе «пол».
- `seatSpot` — `ui/src/features/companion/space/anchors.ts:238` — Куда сесть, когда активным стало окно: правая треть верхнего края, на открытом участке.
- `floorSpot` — `ui/src/features/companion/space/anchors.ts:255` — Место на «полу» у правого края — рабочий стол или развёрнутое окно.
- `sameSurface` — `ui/src/features/companion/space/anchors.ts:264` — Та же опора в новой картине (окно сдвинули): по хозяину и виду.
- `Point` — `ui/src/features/companion/space/chase.ts:20` — —
- `cursorSpot` — `ui/src/features/companion/space/chase.ts:43` — Где встать, чтобы быть рядом с курсором; `body` — где персонаж сейчас (ступни).
- `worthMoving` — `ui/src/features/companion/space/chase.ts:67` — Стоит ли идти: другая опора или заметно другое место на той же.
- `inTheWay` — `ui/src/features/companion/space/chase.ts:74` — Мешает ли персонаж печатать: его фигура рядом с полем ввода (с запасом `gap`).
- `stepAside` — `ui/src/features/companion/space/chase.ts:87` — Куда отойти от поля ввода: по своей опоре в сторону, где места больше, на `away` от него; не выходит —
- `Climb` — `ui/src/features/companion/space/climb.ts:12` — —
- `climbRoute` — `ui/src/features/companion/space/climb.ts:29` — Маршрут с места `from` на верх окна `to` или `null` (прыгать). `bottom` — низ окна-цели: окно должно
- `descendRoute` — `ui/src/features/companion/space/climb.ts:61` — Маршрут спуска с крыши окна `from` вниз на опору `to` или `null` (прыгать): дойти по крыше до края над
- `followSpot` — `ui/src/features/companion/space/control.ts:9` — Место для активного окна (раздел 4.1): край окна, «пол» у правого края или угол экрана.
- `hostOf` — `ui/src/features/companion/space/control.ts:20` — Хозяин места (окно) или `null` для «пола».
- `Release` — `ui/src/features/companion/space/control.ts:24` — —
- `DROP_RADIUS` — `ui/src/features/companion/space/control.ts:31` — Отпустили, держа мышью (как у Capri): Shift — сесть рядом, Ctrl — повиснуть, иначе — бросок.
- `CALM_SPEED` — `ui/src/features/companion/space/control.ts:33` — Отпустили спокойнее этого (px/с) — закрепиться на месте рядом; резче — бросок.
- `dropTarget` — `ui/src/features/companion/space/control.ts:36` — Куда персонаж закрепится, если отпустить здесь: край, угол, бок окна, верх экрана, значок.
- `release` — `ui/src/features/companion/space/control.ts:40` — —
- `velocityOf` — `ui/src/features/companion/space/control.ts:59` — Скорость по следу курсора за последние 80 мс, пикселей в секунду.
- `bubbleText` — `ui/src/features/companion/space/control.ts:71` — Облачко: последние ~140 знаков реплики, целыми словами.
- `placeBubble` — `ui/src/features/companion/space/control.ts:85` — Где поставить облачко размером `size` у фигуры `box` в окне `view` (левый верхний угол): над головой,
- `fitScreen` — `ui/src/features/companion/space/room.ts:17` — —
- `Rect` — `ui/src/features/companion/space/world.ts:5` — Картина рабочего стола от оболочки (`desktop.rs`, физические пиксели экрана) → CSS-пиксели слоя спутника.
- `Seat` — `ui/src/features/companion/space/world.ts:12` — —
- `Focus` — `ui/src/features/companion/space/world.ts:18` — —
- `World` — `ui/src/features/companion/space/world.ts:24` — —
- `rectToCss` — `ui/src/features/companion/space/world.ts:32` — —
- `worldToCss` — `ui/src/features/companion/space/world.ts:42` — Вся картина в CSS-пикселях слоя.

## ui/src/features/edition
Публичный API экрана выбора издания (Этап 20, R-63).

- `EditionBadge.svelte` — `ui/src/features/edition/EditionBadge.svelte:1` — Значок издания в строке статуса (STAGE_20, 3.5): клик — подтверждение и перезапуск на экран выбора.
- `EditionPicker.svelte` — `ui/src/features/edition/EditionPicker.svelte:1` — Экран выбора издания в духе выбора аккаунта Steam (Этап 20, STAGE_20 раздел 3): плитки по центру,
- `EditionId` — `ui/src/features/edition/editions.ts:7` — —
- `Edition` — `ui/src/features/edition/editions.ts:9` — —
- `EDITIONS` — `ui/src/features/edition/editions.ts:20` — Порядок плиток; новое издание — строка здесь и файл `config/editions/<id>.toml`.
- `LauncherState` — `ui/src/features/edition/editions.ts:33` — Что окно помнит между запусками (`launcher.json` в папке настроек приложения).
- `DEFAULT_LAUNCHER` — `ui/src/features/edition/editions.ts:42` — Запоминать — по умолчанию (ускорение запуска, 2026-11-19): окно сразу открывает прошлое издание, экран
- `isEditionId` — `ui/src/features/edition/editions.ts:44` — —
- `editionById` — `ui/src/features/edition/editions.ts:57` — —
- `editionAt` — `ui/src/features/edition/editions.ts:62` — Плитка по номеру; номер вне ряда — первая плитка.
- `parseLauncher` — `ui/src/features/edition/editions.ts:71` — Разбор сохранённого состояния: битое или чужое — умолчания, а не сбой запуска.
- `launcherJson` — `ui/src/features/edition/editions.ts:85` — Как состояние хранится в `launcher.json` (ключ `last` читает и скрипт запуска).
- `needsPicker` — `ui/src/features/edition/editions.ts:94` — Показывать ли экран: при «запоминать» — нет, если не попросили сменить издание явно.
- `needsAgeGate` — `ui/src/features/edition/editions.ts:99` — Нужно ли подтверждение возраста для выбранного издания.
- `PickerAction` — `ui/src/features/edition/editions.ts:103` — —
- `keyAction` — `ui/src/features/edition/editions.ts:107` — Клавиши экрана: ←/→ — фокус по кругу, Enter/Пробел — запуск, 1…9 — сразу плитка.
- `afterPick` — `ui/src/features/edition/editions.ts:119` — Состояние после выбора: издание запоминается как последнее, подтверждение — с датой.
- `LauncherPort` — `ui/src/features/edition/launcher.ts:17` — —
- `launcher` — `ui/src/features/edition/launcher.ts:114` — —
- `PICK_PARAM` — `ui/src/features/edition/launcher.ts:119` — Запрос экрана выбора при перезагрузке окна (смена издания из строки статуса).
- `pickRequested` — `ui/src/features/edition/launcher.ts:121` — —

## ui/src/features/memory
Публичный API редактора памяти (R-63).

- `MemoryPanel.svelte` — `ui/src/features/memory/MemoryPanel.svelte:1` — —

## ui/src/features/metrics
Публичный API фичи метрик: панель (R-63).

- `MetricsPanel.svelte` — `ui/src/features/metrics/MetricsPanel.svelte:1` — —
- `Summary` — `ui/src/features/metrics/stats.ts:7` — —
- `percentile` — `ui/src/features/metrics/stats.ts:28` — Перцентиль по ближайшему рангу: значение из выборки, без интерполяции — честно для малых n.
- `summarize` — `ui/src/features/metrics/stats.ts:36` — —
- `summarizeAll` — `ui/src/features/metrics/stats.ts:49` — Строки панели: сначала стадии с бюджетом (главное), затем остальные по имени.
- `overBudget` — `ui/src/features/metrics/stats.ts:58` — —

## ui/src/features/mic
Публичный API фичи микрофона: приложение монтирует только элемент управления (R-63).

- `CAPTURE_PROCESSOR` — `ui/src/features/mic/capture.worklet.ts:6` — —
- `MIC_SAMPLE_RATE` — `ui/src/features/mic/framer.ts:7` — —
- `MIC_FRAME_SAMPLES` — `ui/src/features/mic/framer.ts:9` — 20 мс при 16 кГц: мельче — лишние кадры, крупнее — запаздывает реакция на голос.
- `FrameSink` — `ui/src/features/mic/framer.ts:13` — —
- `MicFramer` — `ui/src/features/mic/framer.ts:15` — —
- `MicCapture` — `ui/src/features/mic/MicCapture.ts:10` — —
- `MicControl.svelte` — `ui/src/features/mic/MicControl.svelte:1` — —
- `MicMode` — `ui/src/features/mic/mode.ts:5` — —
- `MIC_MODE_VALUES` — `ui/src/features/mic/mode.ts:7` — —
- `micModes` — `ui/src/features/mic/mode.ts:10` — Режимы с подписями на языке издания.
- `TRAILING_SILENCE_MS` — `ui/src/features/mic/mode.ts:15` — Тишина после отпускания клавиши: чуть дольше паузы конца фразы в ядре — фраза закрывается сразу.
- `parseMode` — `ui/src/features/mic/mode.ts:17` — —
- `isPushToTalk` — `ui/src/features/mic/mode.ts:21` — —
- `startMode` — `ui/src/features/mic/mode.ts:26` — Режим при старте: в фоне (ADR-0041) витюбер ждёт зова, поэтому слушает всегда.

## ui/src/features/onboarding
Публичный API мастера первого запуска (R-63).

- `Onboarding.svelte` — `ui/src/features/onboarding/Onboarding.svelte:1` — —
- `SetupItem` — `ui/src/features/onboarding/plan.ts:8` — —
- `initialSelection` — `ui/src/features/onboarding/plan.ts:10` — —
- `toggled` — `ui/src/features/onboarding/plan.ts:15` — Обязательное снять нельзя: без него диалог не заработает.
- `downloadSize` — `ui/src/features/onboarding/plan.ts:28` — Сколько байт ещё скачивать: уже стоящее не считается.
- `canInstall` — `ui/src/features/onboarding/plan.ts:34` — —
- `formatSize` — `ui/src/features/onboarding/plan.ts:42` — —
- `percent` — `ui/src/features/onboarding/plan.ts:49` — —
- `restartApp` — `ui/src/features/onboarding/restart.ts:7` — Модели подхватываются при старте ядра, поэтому после установки приложение перезапускается.

## ui/src/features/radio
Публичный API радио (ADR-0049, BEHAVIOR §8).

- `listenRadioCommands` — `ui/src/features/radio/commands.ts:12` — Главное окно: выполнять команды спутника.
- `sendRadioCommand` — `ui/src/features/radio/commands.ts:19` — Спутник: отправить команду главному окну.
- `RadioPlayer` — `ui/src/features/radio/player.ts:28` — —
- `RadioControl.svelte` — `ui/src/features/radio/RadioControl.svelte:1` — Радио в окне настроек (ADR-0049): включить, ⏮ ⏯ ⏭, станция, громкость, своя станция.
- `Station` — `ui/src/features/radio/stations.ts:5` — Станции и настройки радио (ADR-0049, BEHAVIOR §8): список по умолчанию, свои станции пользователя,
- `DEFAULT_STATIONS` — `ui/src/features/radio/stations.ts:11` — Проверены 2026-11-17: отвечают браузеру потоком MP3/AAC.
- `RadioSettings` — `ui/src/features/radio/stations.ts:21` — —
- `RADIO_KEY` — `ui/src/features/radio/stations.ts:28` — —
- `RadioMode` — `ui/src/features/radio/stations.ts:32` — Что играет радио — для спутника и таблички.
- `RadioFeed` — `ui/src/features/radio/stations.ts:34` — —
- `RadioCommand` — `ui/src/features/radio/stations.ts:41` — —
- `isRadioCommand` — `ui/src/features/radio/stations.ts:43` — —
- `station` — `ui/src/features/radio/stations.ts:48` — Своя станция: только `https:` и непустое имя до 60 знаков; иначе `null`.
- `stationsOf` — `ui/src/features/radio/stations.ts:60` — —
- `step` — `ui/src/features/radio/stations.ts:65` — Следующая (`+1`) или предыдущая (`-1`) станция по кругу.
- `parseRadio` — `ui/src/features/radio/stations.ts:74` — —
- `loadRadio` — `ui/src/features/radio/stations.ts:100` — —
- `saveRadio` — `ui/src/features/radio/stations.ts:108` — —

## ui/src/features/resources
Публичный API фичи ресурсов: панель (R-63).

- `HISTORY_POINTS` — `ui/src/features/resources/history.ts:9` — Снимок приходит раз в секунду: на графике пять минут.
- `LoadHistory` — `ui/src/features/resources/history.ts:11` — —
- `addSnapshot` — `ui/src/features/resources/history.ts:18` — —
- `sparkline` — `ui/src/features/resources/history.ts:30` — Точки SVG `polyline`; новые — справа, вертикальный масштаб — от `maxMb`.
- `stateLabel` — `ui/src/features/resources/history.ts:46` — —
- `ResourcesPanel.svelte` — `ui/src/features/resources/ResourcesPanel.svelte:1` — —

## ui/src/features/skills
Публичный API панели «Навыки» (Этап 23, ADR-0043; R-63).

- `SkillGroup` — `ui/src/features/skills/skills.ts:7` — —
- `groupOf` — `ui/src/features/skills/skills.ts:10` — Включён — «on»; выключен, но плагин работает — «off»; плагин установлен, но не запущен — «idle».
- `grouped` — `ui/src/features/skills/skills.ts:16` — Навыки по группам в порядке панели; поиск — по названию, описанию и примерам, без регистра.
- `needsConfirm` — `ui/src/features/skills/skills.ts:35` — Включение навыка, который ходит в интернет, — только после явного «да» (NFR-06).
- `statsLine` — `ui/src/features/skills/skills.ts:40` — Строка счётчиков: «сработал 3 раза · 12 мс · не успел 1»; не срабатывал — пусто.
- `SkillsPanel.svelte` — `ui/src/features/skills/SkillsPanel.svelte:1` — —

## ui/src/features/theme
Публичный API оформления (ADR-0047; R-63): панель с цветовым кругом и применение темы при старте.

- `Swatch` — `ui/src/features/theme/palette.ts:7` — Точка на круге: оттенок 0…360 и насыщенность 0…1.
- `Theme` — `ui/src/features/theme/palette.ts:12` — —
- `Preset` — `ui/src/features/theme/palette.ts:20` — —
- `DEFAULT_THEME` — `ui/src/features/theme/palette.ts:28` — «Ночь Умника» — палитра по умолчанию (ADR-0046).
- `BUILT_IN` — `ui/src/features/theme/palette.ts:35` — —
- `themeVars` — `ui/src/features/theme/palette.ts:81` — Все переменные темы. Насыщенность основного цвета тянет за собой фон, рамки и текст.
- `applyTheme` — `ui/src/features/theme/palette.ts:106` — Применить к корню документа: переменные `theme.css` перекрываются инлайн-стилем.
- `swatchAt` — `ui/src/features/theme/palette.ts:111` — Точка круга → оттенок и насыщенность; красный сверху, по часовой стрелке (как `conic-gradient`).
- `pointOf` — `ui/src/features/theme/palette.ts:117` — Оттенок и насыщенность → смещение маркера от центра круга.
- `toHex` — `ui/src/features/theme/palette.ts:123` — Цвет маркера (яркость 60%) в `#rrggbb`: показ и ручной ввод в поле.
- `fromHex` — `ui/src/features/theme/palette.ts:137` — `#rrggbb` → оттенок и насыщенность (яркость задаёт роль цвета); не цвет — `null`.
- `THEME_KEY` — `ui/src/features/theme/palette.ts:159` — Ключ текущей темы: другое окно (спутник) узнаёт о смене по событию `storage`.
- `parseTheme` — `ui/src/features/theme/palette.ts:172` — Разбор сохранённой темы; чужое или битое — `null`.
- `loadTheme` — `ui/src/features/theme/palette.ts:200` — —
- `saveTheme` — `ui/src/features/theme/palette.ts:204` — —
- `loadPresets` — `ui/src/features/theme/palette.ts:209` — Встроенные палитры и свои сохранённые.
- `savePreset` — `ui/src/features/theme/palette.ts:236` — Сохранить свою палитру; то же имя — заменить.
- `deletePreset` — `ui/src/features/theme/palette.ts:243` — —
- `ThemePanel.svelte` — `ui/src/features/theme/ThemePanel.svelte:1` — —
