# PROJECT MAP

> Автогенерация: `python -m tools.gen_map`. Не редактировать.

## src/vtuber
Ядро локального ИИ-витюбера.

## src/vtuber/adapters
Адаптеры: реализации портов для конкретных движков.

## src/vtuber/adapters/gpu
Опрос видеокарты для менеджера ресурсов (ADR-0018).

- `NvidiaSmiConfig` — `src/vtuber/adapters/gpu/nvidia_smi.py:22` — Подсекция опроса: срок одного вызова.
- `parse_memory` — `src/vtuber/adapters/gpu/nvidia_smi.py:28` — Первая видеокарта из вывода `nvidia-smi`; непонятный вывод — None.
- `NvidiaSmiProbe` — `src/vtuber/adapters/gpu/nvidia_smi.py:37` — `GpuProbe`: None, если утилиты нет, карта не NVIDIA или вызов не уложился в срок.

## src/vtuber/adapters/llm
Адаптеры языковых моделей (LLMPort).

- `LlamaCppOptions` — `src/vtuber/adapters/llm/config.py:8` — Подсекция `[llm.llamacpp]`: особенности llama-server.
- `GenerationConfig` — `src/vtuber/adapters/llm/config.py:21` — Подсекция `[llm.generation]`: длина и температура ответа диалога (T-07).
- `LLMConfig` — `src/vtuber/adapters/llm/config.py:28` — Какой бэкенд, где он, тайм-ауты (R-36) и параметры генерации.
- `ChildBinding` — `src/vtuber/adapters/llm/job_object.py:15` — Держит описатель задания: пока ядро живо, задание открыто; на других системах пусто.
- `LlamaCppLLM` — `src/vtuber/adapters/llm/llamacpp.py:35` — OpenAI-совместимый стрим + особенности llama-server.
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

## src/vtuber/adapters/stt
Адаптеры голосового ввода: распознавание и детектор речи (ADR-0016).

- `VadConfig` — `src/vtuber/adapters/stt/silero_vad.py:31` — Секция `[stt.vad]`: файл модели и потоки CPU (1 — окно короткое, больше не нужно).
- `SileroVad` — `src/vtuber/adapters/stt/silero_vad.py:46` — Реализует VadPort. Модели нет — отвечает `STTUnavailable`, не падает при старте.
- `WhisperConfig` — `src/vtuber/adapters/stt/whisper.py:34` — Секция `[stt.whisper]`.
- `WhisperSTT` — `src/vtuber/adapters/stt/whisper.py:70` — Реализует STTPort. Модели нет — не падает при старте, отвечает `STTUnavailable`.

## src/vtuber/adapters/tts
Адаптеры синтеза речи (TTSPort).

- `TTSConfig` — `src/vtuber/adapters/tts/config.py:12` — Секция `[tts]`.
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

## src/vtuber/application
Прикладной слой: сценарии диалога и конвейер ответа поверх портов.

## src/vtuber/application/conversation
Сценарий «ход диалога»: реплика → промпт → конвейер → история и события.

- `Branch` — `src/vtuber/application/conversation/branches.py:11` — Ветка — путь до листа: `title` — последняя реплика; `active` — текущий путь через неё.
- `Checkpoint` — `src/vtuber/application/conversation/branches.py:21` — Названное место в диалоге.
- `DialogueTree` — `src/vtuber/application/conversation/branches.py:28` — Хранит все ходы; история промпта — только путь до активного.
- `FirstOutputSink` — `src/vtuber/application/conversation/first_output.py:11` — Пропускает всё в `inner`; на первом выводе ответа зовёт `on_first` (THINKING → SPEAKING).
- `InitiativeConfig` — `src/vtuber/application/conversation/initiative.py:20` — Секция `[initiative]`: выключена по умолчанию, персонаж молчит, пока его не попросят.
- `InitiativeActions` — `src/vtuber/application/conversation/initiative.py:31` — `speak` возвращается, когда реплика прозвучала; `blocked` — занято: ход, речь, набор, фон.
- `Initiative` — `src/vtuber/application/conversation/initiative.py:39` — Считает тишину и говорит, когда её набралось; `user_input` обрывает реплику сразу.
- `ConversationService` — `src/vtuber/application/conversation/service.py:61` — Точка входа сценария «ход диалога» (docs/architecture.md, жизненный цикл хода).

## src/vtuber/application/memory
Память витюбера: история разговора, её резюме и долговременные факты (Этап 10).

- `MemoryEditor` — `src/vtuber/application/memory/editor.py:12` — После правки индекс сверяется сразу: удалённый факт не должен попасть в следующий ответ.
- `MemoryControls` — `src/vtuber/application/memory/editor.py:54` — Что UI может делать с памятью.
- `ExtractedFact` — `src/vtuber/application/memory/fact_extractor.py:32` — Факт из ответа LLM; важность — как её оценила модель.
- `parse_facts` — `src/vtuber/application/memory/fact_extractor.py:47` — Факты из ответа модели; пробелы по краям текста срезаются.
- `FactExtractor` — `src/vtuber/application/memory/fact_extractor.py:66` — Ход → факты о пользователе одним запросом к LLM (низкая temperature — в `params`).
- `FactMemoryConfig` — `src/vtuber/application/memory/facts.py:21` — `dedup_score` — близость (косинус), от которой новый факт считается уже известным.
- `FactMemory` — `src/vtuber/application/memory/facts.py:27` — Факты о пользователе: извлечение (LLM), векторы (эмбеддер), хранилище.
- `MemoryKeeper` — `src/vtuber/application/memory/keeper.py:23` — По каждому записанному ходу: факты — в долговременную память, отрезанное — в резюме.
- `collect` — `src/vtuber/application/memory/llm_text.py:15` — Ответ LLM целиком (фоновым задачам стрим не нужен); поток закрывается при отмене.
- `strip_tags` — `src/vtuber/application/memory/llm_text.py:21` — Текст ответа без тегов эмоций.
- `MemoryEraser` — `src/vtuber/application/memory/privacy.py:12` — Сначала останавливает всё, что ещё может записать, и лишь потом удаляет.
- `needs_memory` — `src/vtuber/application/memory/retrieval_gate.py:49` — Реплика о прошлом разговоре или вопрос о самом пользователе.
- `is_factual_question` — `src/vtuber/application/memory/retrieval_gate.py:56` — Вопрос о мире, а не о пользователе: на нём цена выдумки выше, температура ниже.
- `RetrievalConfig` — `src/vtuber/application/memory/retrieval_gate.py:61` — Секция `[memory.retrieval]`.
- `TurnHints` — `src/vtuber/application/memory/retrieval_gate.py:76` — Что память добавляет ходу: справка в реплику и температура (None — обычная).
- `MemoryRecall` — `src/vtuber/application/memory/retrieval_gate.py:83` — Подсказки хода: факты из памяти, если гейт открыт; сбой памяти ход не задерживает.
- `ShortTermMemory` — `src/vtuber/application/memory/short_term.py:27` — История ходов для промпта (T-04).
- `Summarizer` — `src/vtuber/application/memory/summarizer.py:23` — Прежнее резюме + отрезанные сообщения → новое резюме одним запросом к LLM.
- `VaultedFacts` — `src/vtuber/application/memory/vault_sync.py:31` — `MemoryStorePort`: сначала заметка, потом индекс; сбой записи не оставит факт без файла.
- `reconcile` — `src/vtuber/application/memory/vault_sync.py:56` — Приводит индекс к заметкам: правка главнее индекса, а заметка без разбора его не трогает.
- `VaultWatcher` — `src/vtuber/application/memory/vault_sync.py:88` — Замечает правки опросом: `watchdog` был бы новой зависимостью, а опрос стоит мало (замер).
- `ChatRecorder` — `src/vtuber/application/memory/vault_sync.py:157` — Пишет ходы в заметки своей задачей: подписчик шины только кладёт ход в очередь.
- `without_viewer_turns` — `src/vtuber/application/memory/viewer_filter.py:8` — Без реплик зрителей и ответов на них: иначе зритель попал бы в резюме, а оно — в промпт.

## src/vtuber/application/pipeline
Конвейер ответа: LLM → разбор тегов → нарезка фраз → TTS.

- `ChunkerConfig` — `src/vtuber/application/pipeline/chunker.py:29` — Секция `[pipeline.chunker]`.
- `SentenceChunker` — `src/vtuber/application/pipeline/chunker.py:57` — Один экземпляр на ход: `feed(дельта)` отдаёт готовые фразы, `flush()` — хвост.
- `PipelineConfig` — `src/vtuber/application/pipeline/config.py:8` — Секция `[pipeline]`: нарезка фраз и междометия-заглушки.
- `FillerConfig` — `src/vtuber/application/pipeline/filler.py:26` — Секция `[pipeline.filler]`.
- `FillerBank` — `src/vtuber/application/pipeline/filler.py:38` — Готовые к отдаче междометия; пустой банк (голос не загружен, выключено) — молчит.
- `AudioOut` — `src/vtuber/application/pipeline/filler.py:76` — Единственный писатель звука хода: ответ и междометие не перемешиваются.
- `Voice` — `src/vtuber/application/pipeline/reply_pipeline.py:20` — Голос хода: движок TTS, нарезка на фразы, междометия (T-17); без голоса — только текст.
- `ReplyPipeline` — `src/vtuber/application/pipeline/reply_pipeline.py:62` — Стримит ответ LLM получателю по мере генерации (T-01): ни одна стадия не ждёт конца.
- `Speaker` — `src/vtuber/application/pipeline/speaker.py:29` — Озвучивает фразы одного хода.
- `TextDelta` — `src/vtuber/application/pipeline/stream_parser.py:22` — Порция текста: `text` — для чата, `spoken_text` — для TTS (без эмодзи и разметки).
- `EmotionCue` — `src/vtuber/application/pipeline/stream_parser.py:34` — В ответе встретился тег эмоции; озвучивать нечего.
- `GestureCue` — `src/vtuber/application/pipeline/stream_parser.py:46` — В ответе встретился тег жеста; озвучивать нечего, речь он не задерживает.
- `StreamParser` — `src/vtuber/application/pipeline/stream_parser.py:60` — Разбирает дельты одного ответа по мере поступления (один экземпляр на ход).

## src/vtuber/application/prompting
Сборка промпта: персона, история, динамический блок — от неизменного к изменчивому (T-03).

- `ContextConfig` — `src/vtuber/application/prompting/context_budget.py:12` — Секция `[context]`.
- `ContextBudget` — `src/vtuber/application/prompting/context_budget.py:26` — Приближённый счёт токенов — без запроса к серверу, чтобы не тормозить горячий путь.
- `Prompt` — `src/vtuber/application/prompting/prompt_builder.py:16` — Сообщения для LLM; первые `prefix_length` — неизменный префикс (персона и примеры).
- `PromptBuilder` — `src/vtuber/application/prompting/prompt_builder.py:23` — Строит промпт: [персона + примеры] → [история] → [справка + реплика] (T-03).
- `render_system_prompt` — `src/vtuber/application/prompting/prompt_builder.py:51` — Системный промпт персоны; `{emotions}` в правилах → теги всех эмоций из `Emotion`.

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
- `SetupCatalog` — `src/vtuber/application/setup/catalog.py:39` — `config/catalog.toml`: компоненты, голоса Silero и основная LLM.
- `Recommendation` — `src/vtuber/application/setup/catalog.py:50` — Совет этой машине; `warnings` показываются пользователю как есть.
- `recommend` — `src/vtuber/application/setup/catalog.py:58` — Всё, что помещается; обязательное советуется всегда, но с предупреждением.
- `InstallProgress` — `src/vtuber/application/setup/installer.py:30` — Сколько байт готово из общего числа, какой файл качается.
- `Installer` — `src/vtuber/application/setup/installer.py:57` — Ставит компоненты каталога в корень приложения; пути не выходят за пределы корня.
- `SetupState` — `src/vtuber/application/setup/wizard.py:20` — Что показать: нужен ли мастер, что на машине, что посоветовано и что уже стоит.
- `SetupChoice` — `src/vtuber/application/setup/wizard.py:30` — Что выбрал пользователь в мастере.
- `SetupWizard` — `src/vtuber/application/setup/wizard.py:37` — Ставит только то, что выбрал пользователь; повторный вызов продолжает с места разрыва.

## src/vtuber/application/speech
Подготовка текста к синтезу речи: числа, сокращения, латиница, разметка (S-7.2).

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

- `ToolContext` — `src/vtuber/application/tools/context.py:12` — Опрашивает инструменты параллельно; не успели или упали — ход идёт без них (приоритет 1).

## src/vtuber/application/voice
Голосовой ввод (Этап 11): нарезка речи на фразы, распознавание, перебивание.

- `VoiceConfig` — `src/vtuber/application/voice/listener.py:41` — `interim_ms` — как часто считать промежуточную гипотезу; `min_phrase_ms` — короче не речь.
- `VoiceEvents` — `src/vtuber/application/voice/listener.py:49` — Кто получает голосовой ввод: шлюз (шлёт в UI и начинает ход) или тест.
- `VoiceListener` — `src/vtuber/application/voice/listener.py:65` — Очередь кадров и обработка окон; `feed` не ждёт моделей, `run` — задачей у владельца.
- `SegmenterConfig` — `src/vtuber/application/voice/segmenter.py:15` — Подсекция `[stt.segmenter]`.
- `SpeechStarted` — `src/vtuber/application/voice/segmenter.py:33` — Началась фраза.
- `BargeIn` — `src/vtuber/application/voice/segmenter.py:38` — Речь длится достаточно, чтобы перебить витюбера; один раз на фразу.
- `SpeechEnded` — `src/vtuber/application/voice/segmenter.py:43` — Фраза закончилась; `pcm` — вся фраза с паузой перед ней, без хвоста тишины.
- `Segmenter` — `src/vtuber/application/voice/segmenter.py:52` — Состояние одной линии звука; `feed` принимает окна длиной `window_ms`.

## src/vtuber/bootstrap
Корень композиции: конфиг, персона, сборка графа объектов и точка входа.

- `MemoryConfig` — `src/vtuber/bootstrap/config.py:38` — Секция `[memory]`: фоновая память (Этап 10) — факты и резюме истории в простое.
- `SttConfig` — `src/vtuber/bootstrap/config.py:71` — Секция `[stt]`: голосовой ввод в `serve` (Этап 11, ADR-0016); модели — при первом кадре.
- `AppConfig` — `src/vtuber/bootstrap/config.py:91` — Корень конфига. Только агрегирует: каждую секцию описывает модуль, которому она нужна.
- `load_app_config` — `src/vtuber/bootstrap/config.py:114` — Читает `config/default.toml` и `config/user.toml` из корня проекта `root` поверх `env`.
- `Core` — `src/vtuber/bootstrap/container.py:21` — Общие механизмы, которые получают все: шина событий и телеметрия.
- `Backends` — `src/vtuber/bootstrap/container.py:29` — Внешние движки хода: LLM обязательна, голос — только у шлюза (в терминале нет звука).
- `llm_backends` — `src/vtuber/bootstrap/container.py:40` — Реестр LLM-адаптеров: имя из `[llm].backend` → адаптер (асинхронный контекстный менеджер).
- `tts_backends` — `src/vtuber/bootstrap/container.py:51` — Реестр движков TTS: имя из `[tts].backend` → адаптер; `none` — без голоса (OCP).
- `Conversation` — `src/vtuber/bootstrap/container.py:61` — Собранный диалог: сервис хода, сборщик промпта (прогрев, T-06), история (фоновая память).
- `build_conversation` — `src/vtuber/bootstrap/container.py:69` — Собирает сервис хода; сборщик промпта и история отдаются наружу — прогреву и памяти.
- `LineSource` — `src/vtuber/bootstrap/main.py:67` — Откуда читать строки: `sys.stdin` или его тестовая замена.
- `Console` — `src/vtuber/bootstrap/main.py:74` — Ввод построчно в отдельном потоке — ожидание строки не блокирует цикл (R-34).
- `main` — `src/vtuber/bootstrap/main.py:87` — Код возврата: 0 — штатный выход, 1 — ошибка конфига, 2 — LLM недоступна (чат).
- `run` — `src/vtuber/bootstrap/main.py:307` — Запуск из консоли: `python -m vtuber [chat|serve] [--root путь]`.
- `background_memory` — `src/vtuber/bootstrap/memory.py:48` — Память на время контекста: фон в простое и факты в ходе; выключена — пустой контекст.
- `PersonaConfig` — `src/vtuber/bootstrap/persona.py:13` — Секция `[persona]`: путь к файлу персоны относительно корня проекта.
- `load_persona` — `src/vtuber/bootstrap/persona.py:40` — Читает и проверяет файл персоны; лишний или пропущенный ключ — ошибка.
- `PluginServices` — `src/vtuber/bootstrap/plugins.py:34` — Что плагины дали ядру в `setup`: источники реплик и справку хода.
- `running_plugins` — `src/vtuber/bootstrap/plugins.py:53` — Включённые плагины работают на время контекста; остановка — в обратном порядке.
- `SetupConfig` — `src/vtuber/bootstrap/setup.py:18` — Секция `[setup]`: мастер включён только в поставке; при разработке модели кладут сами.
- `load_catalog` — `src/vtuber/bootstrap/setup.py:38` — Каталог компонентов.
- `render_choice` — `src/vtuber/bootstrap/setup.py:53` — TOML-файл из секций; строки в JSON совпадают со строками TOML, нужных нам значений хватит.
- `write_choice` — `src/vtuber/bootstrap/setup.py:64` — Заменяет файл целиком и атомарно: сбой на середине не оставит битый конфиг.
- `build_wizard` — `src/vtuber/bootstrap/setup.py:72` — Мастер на настоящей сети и диске.
- `LlmSupervised` — `src/vtuber/bootstrap/supervision.py:20` — Сервер, запущенный ядром; внешний не наблюдается: поднять его ядро всё равно не может.
- `ReloadableTTS` — `src/vtuber/bootstrap/supervision.py:42` — Движок голоса, который загружается и выгружается контекстом.
- `TtsSupervised` — `src/vtuber/bootstrap/supervision.py:59` — Голос: сбой виден по флагу, поднять — значит загрузить модель заново и проверить её.
- `VoiceParts` — `src/vtuber/bootstrap/supervision.py:88` — Голос шлюза: движок (грузится при старте), его междометия и обёртка для наблюдателя.
- `build_voice` — `src/vtuber/bootstrap/supervision.py:97` — Голос из конфига; `none` — без голоса.
- `with_voice` — `src/vtuber/bootstrap/supervision.py:107` — Движки хода: конвейер получает обёртку, чтобы сбой голоса был замечен.
- `voice_input` — `src/vtuber/bootstrap/voice_input.py:91` — Подключает микрофон к шлюзу на время контекста; выключено в конфиге — кадры не нужны.
- `AppParts` — `src/vtuber/bootstrap/wiring.py:31` — Что шлюзу нужно от приложения, кроме сервиса хода.
- `connect_memory` — `src/vtuber/bootstrap/wiring.py:43` — Приватный режим работает и без памяти; редактор и очистка честно скажут, что её нет.
- `connect_branches` — `src/vtuber/bootstrap/wiring.py:53` — Дерево начинается с восстановленного разговора: его ветки тоже можно продолжить.
- `connect_panels` — `src/vtuber/bootstrap/wiring.py:63` — Всё, что UI может сделать помимо реплики.
- `connect_initiative` — `src/vtuber/bootstrap/wiring.py:72` — Персонаж сам заговаривает, только если это включили (S-15.1); фон памяти не прерывается.
- `connect_setup` — `src/vtuber/bootstrap/wiring.py:94` — Мастер есть только в поставке: при разработке модели кладут сами.

## src/vtuber/domain
Доменный слой: неизменяемые сущности и значения диалога, речи и эмоций.

- `Role` — `src/vtuber/domain/dialogue.py:11` — Автор сообщения; значения совпадают с ролями OpenAI-совместимого API.
- `AttachedImage` — `src/vtuber/domain/dialogue.py:20` — Картинка к реплике (S-18.1); только в памяти и на один ход.
- `Message` — `src/vtuber/domain/dialogue.py:28` — Одно сообщение контекста LLM.
- `Turn` — `src/vtuber/domain/dialogue.py:37` — Завершённый ход: реплика пользователя и ответ витюбера.
- `Persona` — `src/vtuber/domain/dialogue.py:55` — Характер витюбера, задаётся файлом `personas/*.toml` без правки кода (FR-11).
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
- `CancelReason` — `src/vtuber/domain/events.py:10` — Почему ход прерван.
- `Component` — `src/vtuber/domain/events.py:19` — Бэкенд, о состоянии которого сообщается в UI.
- `BackendState` — `src/vtuber/domain/events.py:27` — Состояние бэкенда для статус-бара UI.
- `TurnStarted` — `src/vtuber/domain/events.py:36` — Ход начат: аватар сразу показывает «думаю» (T-17).
- `TurnRemembered` — `src/vtuber/domain/events.py:43` — Ход записан в историю; `dropped` — сообщения, отрезанные из неё при этом (T-04).
- `TurnFinished` — `src/vtuber/domain/events.py:54` — Ход завершён полностью.
- `TurnCancelled` — `src/vtuber/domain/events.py:61` — Ход прерван; UI сбрасывает аудиобуфер. `message` — что сказать пользователю при ошибке.
- `EmotionChanged` — `src/vtuber/domain/events.py:70` — В ответе встретился тег эмоции.
- `PhraseVoiced` — `src/vtuber/domain/events.py:78` — Фраза озвучена: зазвучит через `starts_in_s` и продлится `duration_s` (субтитры, Этап 12).
- `SearchSource` — `src/vtuber/domain/events.py:91` — Откуда взят ответ: заголовок и адрес страницы.
- `SourcesFound` — `src/vtuber/domain/events.py:99` — Инструмент нашёл источники для этого ответа: UI покажет ссылки (FR-25).
- `BackendNotice` — `src/vtuber/domain/events.py:106` — Сообщение пользователю о компоненте: упал, поднимается, снова работает (S-17.1).
- `ViewerBlocked` — `src/vtuber/domain/events.py:114` — Реплика зрителя похожа на атаку и не дошла до модели; ведущий видит это в UI (FR-31).
- `MetricRecorded` — `src/vtuber/domain/events.py:122` — Замер стадии хода; `turn_id` — None, если замер вне хода (например, прогрев).
- `BackendStatusChanged` — `src/vtuber/domain/events.py:131` — Бэкенд загрузился, упал или восстановился.
- `GpuMemory` — `src/vtuber/domain/gpu.py:7` — Сколько видеопамяти всего и сколько занято всеми программами.
- `IncomingMessage` — `src/vtuber/domain/incoming.py:7` — Реплика из источника `source` (например, `twitch`) от автора `author`.
- `EmbedKind` — `src/vtuber/domain/memory.py:14` — Что кодируется: у e5 запрос и запоминаемый текст кодируются по-разному.
- `FactSource` — `src/vtuber/domain/memory.py:21` — Откуда факт: от этого зависит доверие к нему при ответе.
- `Fact` — `src/vtuber/domain/memory.py:33` — Одна запоминаемая мысль; `importance` 0…1 — что вспоминать в первую очередь.
- `VaultScan` — `src/vtuber/domain/memory.py:55` — Заметки фактов: разобранные и те, что сейчас не читаются (их имена).
- `FactHit` — `src/vtuber/domain/memory.py:63` — Найденный факт; `score` — косинусная близость к запросу, −1…1, больше — ближе.
- `AudioFormat` — `src/vtuber/domain/speech.py:11` — Формат звука: PCM s16le, моно — так звук передаётся в UI (ADR-0003).
- `AudioChunk` — `src/vtuber/domain/speech.py:23` — Непрерывный фрагмент PCM в формате `format`.
- `TurnState` — `src/vtuber/domain/turn_state.py:10` — Где сейчас ход: ждём реплику, думаем, говорим, прерваны.
- `next_state` — `src/vtuber/domain/turn_state.py:30` — Возвращает `target`, если переход из `current` разрешён.
- `looks_like_attack` — `src/vtuber/domain/viewer.py:69` — Явная попытка отменить правила, сменить роль, выманить настройки или подделать разметку.
- `viewer_line` — `src/vtuber/domain/viewer.py:77` — Реплика зрителя для промпта и истории; подделать кавычки и подпись из текста нельзя.
- `is_viewer_line` — `src/vtuber/domain/viewer.py:84` — Реплика в истории — от зрителя, а не от ведущего.

## src/vtuber/gateway
Шлюз: протокол UI ↔ Ядро, кодек, WebSocket-сервер и терминальный чат (M1).

- `shown_text` — `src/vtuber/gateway/branch_bridge.py:19` — Ответ в истории хранится с тегами эмоций; в чате их быть не должно.
- `BranchBridge` — `src/vtuber/gateway/branch_bridge.py:44` — Переход отменяет идущий ответ и заменяет историю промпта: модель видит только новую ветку.
- `AudioFrame` — `src/vtuber/gateway/codec.py:24` — Разобранный аудиокадр.
- `MicFrame` — `src/vtuber/gateway/codec.py:33` — Разобранный кадр микрофона: PCM s16le моно от UI (Этап 11).
- `encode_mic_frame` — `src/vtuber/gateway/codec.py:40` — Кадр микрофона: 8 байт заголовка + PCM; так его собирает UI (`core/frames.ts`).
- `decode_mic_frame` — `src/vtuber/gateway/codec.py:50` — Разбирает бинарный кадр от UI; проверка один раз на границе.
- `decode_inbound` — `src/vtuber/gateway/codec.py:71` — Сообщение от UI; проверка один раз на границе (принцип 6 архитектуры).
- `encode_outbound` — `src/vtuber/gateway/codec.py:86` — JSON-строка сообщения для UI (сериализация pydantic-core, без лишних пробелов).
- `encode_audio_frame` — `src/vtuber/gateway/codec.py:91` — Бинарный кадр: 16 байт заголовка + PCM s16le моно; `seq` по модулю 2^16.
- `decode_audio_frame` — `src/vtuber/gateway/codec.py:99` — Разбирает аудиокадр (тесты; кадры микрофона — Этап 11).
- `ExternalTurns` — `src/vtuber/gateway/external_turns.py:17` — Отвечает на реплики по одной и только в тишине: зритель не обрывает речь витюбера.
- `MemoryBridge` — `src/vtuber/gateway/memory_bridge.py:16` — Список запрашивается только при открытой панели: чтение заметок не должно идти просто так.
- `Panels` — `src/vtuber/gateway/panels.py:37` — Панель не подключена — её сообщения просто не нужны.
- `PrivacyBridge` — `src/vtuber/gateway/privacy_bridge.py:17` — Режим держит сервис хода, а UI получает его состояние при каждом подключении.
- `turn_ref` — `src/vtuber/gateway/protocol.py:38` — Номер хода в JSON-сообщениях: `t-000042` (в аудиокадре — uint64).
- `ErrorCode` — `src/vtuber/gateway/protocol.py:43` — Что пошло не так — UI выбирает реакцию по коду, текст показывает пользователю.
- `SendData` — `src/vtuber/gateway/protocol.py:52` — Реплика пользователя.
- `TypingData` — `src/vtuber/gateway/protocol.py:58` — Черновик реплики, пока пользователь печатает; пустой — поле очищено.
- `DeltaData` — `src/vtuber/gateway/protocol.py:64` — Порция текста ответа.
- `EmotionData` — `src/vtuber/gateway/protocol.py:70` — Эмоция аватара; `intensity` 0…1 (затухание — Этап 8).
- `CancelledData` — `src/vtuber/gateway/protocol.py:77` — Почему ход прерван; `message` — текст ошибки при `reason == "error"`.
- `SpanData` — `src/vtuber/gateway/protocol.py:84` — Замер стадии хода для панели метрик (FR-15).
- `StatusData` — `src/vtuber/gateway/protocol.py:91` — Состояние бэкенда для статус-бара.
- `ErrorData` — `src/vtuber/gateway/protocol.py:98` — Ошибка для пользователя.
- `ChatSend` — `src/vtuber/gateway/protocol.py:105` — UI → Ядро: новая реплика; прерывает текущий ход.
- `ChatCancel` — `src/vtuber/gateway/protocol.py:113` — UI → Ядро: остановить ответ.
- `InputTyping` — `src/vtuber/gateway/protocol.py:121` — UI → Ядро: черновик реплики (с дебаунсом ~300 мс) — прогрев кэша LLM, T-05.
- `TurnStartedMessage` — `src/vtuber/gateway/protocol.py:149` — Ядро → UI: ход начат — аватар «думает» (T-17).
- `ChatDelta` — `src/vtuber/gateway/protocol.py:163` — Ядро → UI: порция текста ответа.
- `AvatarEmotion` — `src/vtuber/gateway/protocol.py:177` — Ядро → UI: сменить выражение аватара.
- `TurnFinishedMessage` — `src/vtuber/gateway/protocol.py:191` — Ядро → UI: ответ закончен полностью.
- `TurnCancelledMessage` — `src/vtuber/gateway/protocol.py:205` — Ядро → UI: ход прерван — UI сбрасывает аудиобуфер.
- `MetricsSpan` — `src/vtuber/gateway/protocol.py:219` — Ядро → UI: замер стадии; `turn` — None вне хода (прогрев).
- `Status` — `src/vtuber/gateway/protocol.py:233` — Ядро → UI: состояние бэкенда (вне хода).
- `InputBargeIn` — `src/vtuber/gateway/protocol.py:246` — Ядро → UI: пользователь заговорил — оборвать голос витюбера сразу (Этап 11).
- `InputHypothesis` — `src/vtuber/gateway/protocol.py:259` — Ядро → UI: промежуточный текст фразы пользователя.
- `InputFinal` — `src/vtuber/gateway/protocol.py:272` — Ядро → UI: распознанная фраза — реплика пользователя в чате; за ней начнётся ход.
- `ErrorMessage` — `src/vtuber/gateway/protocol.py:285` — Ядро → UI: ошибка; `turn` — None, если не относится к ходу (битое сообщение).
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
- `VisibilityData` — `src/vtuber/gateway/protocol_presence.py:8` — Видно ли окно.
- `WindowVisibility` — `src/vtuber/gateway/protocol_presence.py:14` — UI → Ядро: окно свернули или вернули; свёрнутому персонаж сам не заговорит (S-15.1).
- `ImageData` — `src/vtuber/gateway/protocol_vision.py:12` — Картинка; UI уменьшает её заранее.
- `SendImageData` — `src/vtuber/gateway/protocol_vision.py:19` — Реплика с картинкой.
- `ChatSendImage` — `src/vtuber/gateway/protocol_vision.py:26` — UI → Ядро: новая реплика с картинкой; прерывает текущий ход, как `chat.send`.
- `ResourcesFeed` — `src/vtuber/gateway/resources_feed.py:15` — Закрытая панель ничего не считает: задачи нет, пока UI не попросит.
- `GatewayConfig` — `src/vtuber/gateway/server.py:61` — Секция `[gateway]`: где слушать UI (только localhost, ADR-0002).
- `GatewayServer` — `src/vtuber/gateway/server.py:68` — Шлюз для UI: `async with GatewayServer(...) as server: await server.serve_forever()`.
- `SetupBridge` — `src/vtuber/gateway/setup_bridge.py:22` — Переводит сообщения UI в вызовы мастера; ход установки шлёт реже, чем приходят данные.
- `WsReplySink` — `src/vtuber/gateway/sink.py:15` — ReplySink для WebSocket: текст → `chat.delta`, эмоция → `avatar.emotion`, звук → кадр.
- `TerminalSink` — `src/vtuber/gateway/terminal.py:29` — ReplySink для консоли: печатает ответ по мере генерации и помнит время первой порции.
- `TerminalChat` — `src/vtuber/gateway/terminal.py:69` — Цикл чата: строка → ход; новая строка во время ответа прерывает его (T-14).
- `VoiceBridge` — `src/vtuber/gateway/voice_bridge.py:17` — Реализует `VoiceEvents`: перебивание, гипотезы в UI, финальная фраза — новый ход.

## src/vtuber/kernel
Общие механизмы ядра: шина событий, реестр, телеметрия, конфиг, логи.

- `EventBus` — `src/vtuber/kernel/bus.py:15` — Доставляет событие подписчикам его точного типа (не подклассов), параллельно.
- `ConfigSection` — `src/vtuber/kernel/config.py:21` — База секции конфига: неизменяема, лишний ключ — ошибка (опечатка не пройдёт молча).
- `ConfigFiles` — `src/vtuber/kernel/config.py:32` — Файлы конфигурации: `default` обязателен, остальные — если есть.
- `load_config` — `src/vtuber/kernel/config.py:49` — Собирает конфиг из файлов и окружения и проверяет его моделью `model`.
- `current_turn` — `src/vtuber/kernel/context.py:14` — Номер текущего хода или None вне хода; чтение — десятки наносекунд (горячий путь).
- `turn_context` — `src/vtuber/kernel/context.py:20` — Внутри блока ход `turn_id` — текущий для метрик, а логи несут поле `turn_id`.
- `LoggingConfig` — `src/vtuber/kernel/logging.py:16` — Секция `[logging]`; `file` открывает bootstrap (относительно корня проекта).
- `configure_logging` — `src/vtuber/kernel/logging.py:23` — Настраивает structlog: одна JSON-строка на событие в `stream`.
- `logging_to` — `src/vtuber/kernel/logging.py:45` — Логи идут в `stream` на время блока; на выходе — настройка по умолчанию.
- `get_logger` — `src/vtuber/kernel/logging.py:58` — Логгер модуля; имя попадает в поле `module` каждого события.
- `ContextTool` — `src/vtuber/kernel/plugin.py:33` — Инструмент и его срок; `None` — обычный короткий срок из `[plugins]`.
- `PluginsConfig` — `src/vtuber/kernel/plugin.py:46` — Секция `[plugins]`: что включено и настройки каждого плагина в `settings.<имя>`.
- `PluginContext` — `src/vtuber/kernel/plugin.py:59` — Доступ плагина к ядру: подписка на события, своя секция конфига, логгер.
- `Plugin` — `src/vtuber/kernel/plugin.py:162` — Плагин: entry point группы `vtuber.plugins` указывает на его класс или фабрику.
- `Registry` — `src/vtuber/kernel/registry.py:8` — Имя → фабрика `A → T`; например, `Registry[TTSConfig, TTSPort]` для движков TTS.
- `TelemetryConfig` — `src/vtuber/kernel/telemetry.py:23` — Секция `[telemetry]`; `traces_file` открывает bootstrap (относительно корня проекта).
- `Telemetry` — `src/vtuber/kernel/telemetry.py:29` — Замеряет стадии хода и отдаёт метрики в шину фоновой задачей `run`.
- `Span` — `src/vtuber/kernel/telemetry.py:63` — Контекстный менеджер одного замера; создаётся `Telemetry.span`.
- `TraceWriter` — `src/vtuber/kernel/telemetry.py:88` — Подписчик шины: пишет каждую метрику JSON-строкой в поток (`logs/traces.jsonl`).

## src/vtuber/ports
Порты: Protocol-интерфейсы, через которые ядро обращается к внешнему миру.

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
- `VadPort` — `src/vtuber/ports/stt.py:12` — Детектор речи: окно PCM → вероятность, что это речь.
- `STTPort` — `src/vtuber/ports/stt.py:44` — Распознавание отрезка речи.
- `TTSPort` — `src/vtuber/ports/tts.py:9` — Движок TTS; адаптеры бросают только доменные ошибки (R-43).

## ui/src/app
—

- `App.svelte` — `ui/src/app/App.svelte:1` — Окно: чат слева, сцена с аватаром справа (FR-01), статус-бар внизу, панель метрик по горячей
- `DEFAULT_RATIO` — `ui/src/app/split.ts:7` — Чат 2 : сцена 3 — как в каркасе S-5.1.
- `MIN_CHAT_PX` — `ui/src/app/split.ts:9` — Уже — чат не читается, сцена теряет модель.
- `MIN_STAGE_PX` — `ui/src/app/split.ts:10` — —
- `KEYBOARD_STEP` — `ui/src/app/split.ts:12` — Шаг стрелками на разделителе — доступность с клавиатуры.
- `RatioStorage` — `ui/src/app/split.ts:17` — Минимальное хранилище: в тестах — Map-подобная подмена.
- `clampRatio` — `ui/src/app/split.ts:20` — Доля в пределах, при которых обе панели не уже своего минимума.
- `ratioAt` — `ui/src/app/split.ts:30` — Доля по положению указателя внутри раскладки.
- `loadRatio` — `ui/src/app/split.ts:35` — Сохранённая доля или умолчание; битое значение или недоступное хранилище — умолчание.
- `saveRatio` — `ui/src/app/split.ts:45` — Запомнить долю; ошибка хранилища (переполнено, запрещено) не ломает раскладку.
- `SplitLayout.svelte` — `ui/src/app/SplitLayout.svelte:1` — Две панели с перетаскиваемым разделителем (FR-01). Доля — в split.ts: ограничение минимумами
- `Tone` — `ui/src/app/status.ts:8` — —
- `Indicator` — `ui/src/app/status.ts:10` — —
- `connectionIndicator` — `ui/src/app/status.ts:15` — —
- `backendIndicator` — `ui/src/app/status.ts:37` — Состояние бэкенда, пока связи нет, — устаревшее: показываем «—», а не последнее известное.
- `blockedDetails` — `ui/src/app/status.ts:42` — Подсказка над счётчиком: кто и что написал; решение — за ведущим (`/пауза`, FR-31).
- `StatusBar.svelte` — `ui/src/app/StatusBar.svelte:1` — Статус-бар: связь с ядром и состояние бэкендов (LLM, TTS). Тексты и цвета — status.ts.

## ui/src/core
Публичный API core: фичи импортируют отсюда, а не из модулей пакета (R-63).

- `FrameScheduler` — `ui/src/core/batch.ts:8` — Запланировать вызов перед следующей отрисовкой; в окне — `requestAnimationFrame`.
- `animationFrame` — `ui/src/core/batch.ts:10` — —
- `FrameBatch` — `ui/src/core/batch.ts:20` — Очередь изменений до следующего кадра. Порядок сохраняется: смена связи и сообщения ядра идут
- `AudioSink` — `ui/src/core/client.ts:19` — —
- `CancelSink` — `ui/src/core/client.ts:21` — Звук хода надо оборвать: `turn` — отменённый ход, null — связь потеряна (сбросить всё).
- `CoreClientOptions` — `ui/src/core/client.ts:23` — —
- `CoreClient` — `ui/src/core/client.ts:32` — —
- `AUDIO_HEADER_SIZE` — `ui/src/core/frames.ts:11` — Заголовок аудиокадра `<BBHIQ`: тип, версия, seq, sample_rate, turn_id — docs/protocol.md.
- `MIC_HEADER_SIZE` — `ui/src/core/frames.ts:16` — Заголовок кадра микрофона `<BBHI`: тип, версия, seq, sample_rate.
- `encodeMicFrame` — `ui/src/core/frames.ts:20` — Кадр микрофона для ядра: заголовок + PCM s16le моно.
- `AudioFrame` — `ui/src/core/frames.ts:37` — Аудиокадр ядра. `turn` — в том же виде, что в JSON-сообщениях, чтобы их сопоставлять.
- `FrameError` — `ui/src/core/frames.ts:45` — Кадр не соответствует протоколу: ядро другой версии или повреждённые данные.
- `turnRef` — `ui/src/core/frames.ts:80` — Номер хода из аудиокадра в виде JSON-сообщений.
- `parseMessage` — `ui/src/core/frames.ts:104` — Текстовый кадр → сообщение ядра; `FrameError`, если это не сообщение протокола.
- `decodeAudioFrame` — `ui/src/core/frames.ts:121` — Бинарный кадр → аудиокадр. PCM не копируется: `Int16Array` смотрит в тот же буфер
- `FIRST_CHAR_SPAN` — `ui/src/core/probe.ts:8` — —
- `FirstCharProbe` — `ui/src/core/probe.ts:10` — —
- `FIRST_AUDIO_SPAN` — `ui/src/core/probe.ts:57` — —
- `FirstAudioProbe` — `ui/src/core/probe.ts:64` — Замер UI «реплика отправлена → звук ответа зазвучал» — настоящий TTFA (NFR-02: p50 ≤ 800 мс):
- `protocol.gen.ts` — `ui/src/core/protocol.gen.ts:1` — Автогенерация: `uv run python tools/gen_protocol.py`. Не редактировать.
- `int16ToFloat` — `ui/src/core/resample.ts:11` — Сэмплы s16 → float [-1, 1).
- `StreamResampler` — `ui/src/core/resample.ts:19` — —
- `Role` — `ui/src/core/store.svelte.ts:25` — —
- `MessageStatus` — `ui/src/core/store.svelte.ts:26` — —
- `TurnPhase` — `ui/src/core/store.svelte.ts:28` — Фаза хода для аватара и кнопки «Стоп»: ждём первый токен / идёт ответ / ничего.
- `ChatMessage` — `ui/src/core/store.svelte.ts:30` — —
- `BranchesView` — `ui/src/core/store.svelte.ts:44` — —
- `PrivacyView` — `ui/src/core/store.svelte.ts:46` — —
- `SPAN_HISTORY` — `ui/src/core/store.svelte.ts:52` — —
- `SpeechProgress` — `ui/src/core/store.svelte.ts:55` — Что звучит в плеере (сообщает фича звука): ход, идёт ли звук, сыграно и получено, секунд.
- `VoiceState` — `ui/src/core/store.svelte.ts:66` — Голос в UI. Ход ядра заканчивается, когда синтез готов, а звучит голос дольше (синтез
- `AppStore` — `ui/src/core/store.svelte.ts:71` — —
- `CLOSE_REPLACED` — `ui/src/core/transport.ts:10` — Код закрытия «вытеснен новым клиентом» — `gateway/server.py` (ADR-0008).
- `SocketLike` — `ui/src/core/transport.ts:14` — Часть WebSocket, нужная транспорту: в тестах подменяется фейком.
- `SocketFactory` — `ui/src/core/transport.ts:24` — —
- `ConnectionState` — `ui/src/core/transport.ts:27` — `replaced` — ядро приняло другое окно; переподключаться нельзя, иначе окна вытесняют друг друга.
- `TransportListener` — `ui/src/core/transport.ts:29` — —
- `Backoff` — `ui/src/core/transport.ts:37` — Пауза перед попыткой n (с нуля): `min(maxMs, initialMs · factor^n)`.
- `TransportOptions` — `ui/src/core/transport.ts:43` — —
- `Transport` — `ui/src/core/transport.ts:66` — —

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
Публичный API фичи аватара: сцена и контракт рендера (ADR-0011).

- `AvatarSource` — `ui/src/features/avatar/AvatarRenderer.ts:13` — Что загрузить: файлы модели в `ui/public/avatars/<имя>/` (ADR-0011).
- `AvatarReaction` — `ui/src/features/avatar/AvatarRenderer.ts:24` — Реакция на ход разговора, не зависящая от текста: «слушаю» (пользователь печатает),
- `StageSize` — `ui/src/features/avatar/AvatarRenderer.ts:27` — Размер области сцены в CSS-пикселях; рендер сам учитывает devicePixelRatio.
- `AvatarRenderer` — `ui/src/features/avatar/AvatarRenderer.ts:32` — —
- `AvatarStage.svelte` — `ui/src/features/avatar/AvatarStage.svelte:1` — Сцена с аватаром: холст Live2D на всю панель, статус загрузки или ошибки поверх. Логика —
- `HeadAxis` — `ui/src/features/avatar/gesture.ts:6` — —
- `GestureSpec` — `ui/src/features/avatar/gesture.ts:8` — —
- `gestureAngle` — `ui/src/features/avatar/gesture.ts:18` — Добавка к углу головы через `elapsedMs`; огибающая возвращает голову на место к концу жеста.
- `MAX_DELTA_MS` — `ui/src/features/avatar/loop.ts:7` — Шаг после паузы или подвисания ограничен: иначе физика волос «выстрелит» за один кадр.
- `FrameSource` — `ui/src/features/avatar/loop.ts:10` — Источник кадров: в окне — `requestAnimationFrame`, в тестах — ручной.
- `Visibility` — `ui/src/features/avatar/loop.ts:16` — Видимость окна: `onChange` возвращает функцию отписки.
- `browserFrames` — `ui/src/features/avatar/loop.ts:21` — —
- `browserVisibility` — `ui/src/features/avatar/loop.ts:28` — —
- `AvatarLoop` — `ui/src/features/avatar/loop.ts:38` — —
- `MAPPING_VERSION` — `ui/src/features/avatar/mapping.ts:10` — —
- `MotionRef` — `ui/src/features/avatar/mapping.ts:12` — —
- `ReactionSpec` — `ui/src/features/avatar/mapping.ts:17` — —
- `FrameSpec` — `ui/src/features/avatar/mapping.ts:25` — Кадр поверх «вписать целиком»: масштаб и сдвиг центра в долях сцены (y — вниз).
- `LipsyncSpec` — `ui/src/features/avatar/mapping.ts:32` — Форма рта при речи (ADR-0023): параметр модели и насколько сильно его двигать.
- `AvatarMapping` — `ui/src/features/avatar/mapping.ts:38` — —
- `DEFAULT_MAPPING` — `ui/src/features/avatar/mapping.ts:50` — Маппинга нет — модель как есть: без выражений и реакций, кадр «вписать целиком».
- `MappingError` — `ui/src/features/avatar/mapping.ts:80` — —
- `parseMapping` — `ui/src/features/avatar/mapping.ts:217` — JSON маппинга → проверенный маппинг; ошибка называет поле и что с ним не так.
- `expressionFor` — `ui/src/features/avatar/mapping.ts:237` — Какое выражение должно быть на лице: реакция (например, «думаю» до первого токена) важнее
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
- `avatarSource` — `ui/src/features/avatar/session.ts:12` — Файлы модели `<имя>` в `ui/public/avatars/<имя>/` (ADR-0011).
- `MouthSource` — `ui/src/features/avatar/session.ts:21` — Открытие рта 0…1 за прошедшие `deltaMs`; без звука — всегда 0.
- `ActivitySource` — `ui/src/features/avatar/session.ts:23` — Идёт ли разговор (ход или голос): пока да — эмоция не угасает.
- `AvatarStatus` — `ui/src/features/avatar/session.ts:25` — —
- `RendererFactory` — `ui/src/features/avatar/session.ts:29` — Создатель рендера: Live2D в окне, фейк в тестах.
- `AvatarSession` — `ui/src/features/avatar/session.ts:35` — —

## ui/src/features/avatar/live2d
—

- `CUBISM_CORE_URL` — `ui/src/features/avatar/live2d/core-loader.ts:8` — Где Vite отдаёт Core из `ui/public/live2d/`.
- `CORE_MISSING_MESSAGE` — `ui/src/features/avatar/live2d/core-loader.ts:10` — —
- `MAX_CORE_MAJOR` — `ui/src/features/avatar/live2d/core-loader.ts:18` — Старший номер Core, с которым работает движок: Core 6 (SDK 5-r.5) убрал
- `formatCoreVersion` — `ui/src/features/avatar/live2d/core-loader.ts:21` — Версия Core из `csmGetVersion()`: 0xMMmmpppp.
- `unsupportedCoreMessage` — `ui/src/features/avatar/live2d/core-loader.ts:25` — —
- `ScriptHost` — `ui/src/features/avatar/live2d/core-loader.ts:33` — Части `window`/`document`, нужные загрузчику: в тестах — подмена.
- `browserHost` — `ui/src/features/avatar/live2d/core-loader.ts:55` — —
- `loadCubismCore` — `ui/src/features/avatar/live2d/core-loader.ts:82` — Подключить Core один раз на окно; повторные вызовы ждут ту же загрузку.
- `Engine` — `ui/src/features/avatar/live2d/engine.ts:9` — —
- `Pixi` — `ui/src/features/avatar/live2d/engine.ts:10` — —
- `Model` — `ui/src/features/avatar/live2d/engine.ts:11` — —
- `CubismInternal` — `ui/src/features/avatar/live2d/engine.ts:12` — —
- `loadEngine` — `ui/src/features/avatar/live2d/engine.ts:22` — —
- `mouthIndices` — `ui/src/features/avatar/live2d/engine.ts:36` — Индексы параметров рта: ищутся один раз при загрузке, в кадре — запись по индексу.
- `headPitchIndices` — `ui/src/features/avatar/live2d/engine.ts:42` — Индексы наклона головы для кивка; у модели без параметра — пусто, кивка нет.
- `mouthFormIndices` — `ui/src/features/avatar/live2d/engine.ts:47` — Индексы формы рта; `declared` — из `mapping.json`. У модели без параметра список пуст.
- `headAxisIndices` — `ui/src/features/avatar/live2d/engine.ts:52` — Индексы параметров головы по осям для жестов; нет параметра — жест по этой оси не виден.
- `Size` — `ui/src/features/avatar/live2d/fit.ts:3` — —
- `Placement` — `ui/src/features/avatar/live2d/fit.ts:8` — —
- `FIT_MARGIN` — `ui/src/features/avatar/live2d/fit.ts:16` — Поля вокруг модели, доля сцены: не упираться в края при наклонах головы и физике волос.
- `fitModel` — `ui/src/features/avatar/live2d/fit.ts:19` — Масштаб «вписать целиком» с полями; модель по центру. Пустая сцена или модель — масштаб 0.
- `applyFrame` — `ui/src/features/avatar/live2d/fit.ts:32` — Кадр маппинга (масштаб и сдвиг центра в долях сцены) поверх «вписать целиком».
- `gazeAt` — `ui/src/features/avatar/live2d/fit.ts:48` — Курсор → взгляд: -1…1 по осям, y вверх (как `AvatarRenderer.lookAt`). За пределами сцены
- `Live2DRenderer` — `ui/src/features/avatar/live2d/Live2DRenderer.ts:33` — —
- `Fetcher` — `ui/src/features/avatar/live2d/settings.ts:8` — —
- `loadMapping` — `ui/src/features/avatar/live2d/settings.ts:23` — `mapping.json` модели; нет файла — модель как есть, битый файл — ошибка с полем.
- `withExpressions` — `ui/src/features/avatar/live2d/settings.ts:46` — Копия model3.json с выражениями маппинга (поверх одноимённых из манифеста) и `url` — по нему
- `loadSettings` — `ui/src/features/avatar/live2d/settings.ts:67` — Манифест модели с выражениями из маппинга — готов для `Live2DModel.from`.

## ui/src/features/chat
Публичный API фичи чата: приложение монтирует только панель (R-63).

- `BranchBar.svelte` — `ui/src/features/chat/BranchBar.svelte:1` — Ветки диалога (S-16.1): показывается, когда есть что выбирать или куда вернуться.
- `Chat.svelte` — `ui/src/features/chat/Chat.svelte:1` — Панель чата: история, индикатор «печатает», ошибка ядра, поле ввода, режим субтитров.
- `Composer.svelte` — `ui/src/features/chat/Composer.svelte:1` — Поле ввода: Enter — отправить, Shift+Enter — перенос, Esc или «Стоп» — прервать ответ.
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
- `MessageList.svelte` — `ui/src/features/chat/MessageList.svelte:1` — Виртуализированная история: в DOM только окно вокруг экрана (layout.ts), строки
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

## ui/src/features/desktop
Публичный API режима «персонаж поверх рабочего стола» (S-15.2).

- `POLL_MS` — `ui/src/features/desktop/clickThrough.ts:9` — 10 раз в секунду: реакция незаметна глазу, а обращения к оболочке не мешают рендеру (NFR-05).
- `ClickThrough` — `ui/src/features/desktop/clickThrough.ts:13` — —
- `DesktopOverlay.svelte` — `ui/src/features/desktop/DesktopOverlay.svelte:1` — Кнопки режима поверх стола и работа с окном. Кнопки видны всегда, а не только над моделью:
- `OVERLAY_SIZE` — `ui/src/features/desktop/mode.ts:9` — Размер небольшого окна с моделью, CSS-пиксели: модель видна целиком и не занимает экран.
- `DesktopState` — `ui/src/features/desktop/mode.ts:11` — —
- `Point` — `ui/src/features/desktop/mode.ts:16` — —
- `WindowPort` — `ui/src/features/desktop/mode.ts:22` — Что режиму нужно от окна. Все вызовы асинхронны: это обращения к оболочке.
- `DesktopStorage` — `ui/src/features/desktop/mode.ts:34` — Нужное от localStorage: в тестах — словарь.
- `loadDesktop` — `ui/src/features/desktop/mode.ts:42` — Запись могла испортиться или устареть: тогда обычное окно, а не сюрприз при запуске.
- `saveDesktop` — `ui/src/features/desktop/mode.ts:60` — —
- `isDesktopHotkey` — `ui/src/features/desktop/mode.ts:65` — Хоткей: окно без рамки, а кнопка может оказаться за краем экрана.
- `DESKTOP_HOTKEY_LABEL` — `ui/src/features/desktop/mode.ts:74` — —
- `tauriWindow` — `ui/src/features/desktop/tauriWindow.ts:9` — —

## ui/src/features/memory
Публичный API редактора памяти (R-63).

- `MEMORY_HOTKEY_LABEL` — `ui/src/features/memory/index.ts:6` — —
- `isMemoryHotkey` — `ui/src/features/memory/index.ts:9` — По `code`, а не `key`: в русской раскладке `key` для этой клавиши — «Н».
- `MemoryPanel.svelte` — `ui/src/features/memory/MemoryPanel.svelte:1` — Редактор памяти (S-16.2): что витюбер запомнил, откуда это и как исправить.

## ui/src/features/metrics
Публичный API фичи метрик: панель и её горячая клавиша (R-63).

- `METRICS_HOTKEY_LABEL` — `ui/src/features/metrics/hotkey.ts:5` — Горячая клавиша панели метрик (FR-15): Ctrl+Shift+M. F12 занят инструментами разработчика
- `isMetricsHotkey` — `ui/src/features/metrics/hotkey.ts:10` — По `code`, а не `key`: в русской раскладке `key` для этой клавиши — «Ь».
- `MetricsPanel.svelte` — `ui/src/features/metrics/MetricsPanel.svelte:1` — Панель метрик для разработчика (FR-15): задержки стадий хода — от ядра (`metrics.span`) и
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
- `MicControl.svelte` — `ui/src/features/mic/MicControl.svelte:1` — Голосовой ввод: режим «выключен / всегда слушать / по клавише F9» (FR-голос, Этап 11). Захват
- `MicMode` — `ui/src/features/mic/mode.ts:3` — —
- `MIC_MODES` — `ui/src/features/mic/mode.ts:5` — —
- `TRAILING_SILENCE_MS` — `ui/src/features/mic/mode.ts:12` — Тишина после отпускания клавиши: чуть дольше паузы конца фразы в ядре — фраза закрывается сразу.
- `parseMode` — `ui/src/features/mic/mode.ts:14` — —
- `isPushToTalk` — `ui/src/features/mic/mode.ts:18` — —

## ui/src/features/onboarding
Публичный API мастера первого запуска (R-63).

- `chosenAvatar` — `ui/src/features/onboarding/avatar.ts:4` — —
- `chooseAvatar` — `ui/src/features/onboarding/avatar.ts:8` — —
- `Onboarding.svelte` — `ui/src/features/onboarding/Onboarding.svelte:1` — Мастер первого запуска (S-13.2): что подходит этой машине, согласие на загрузку, ход загрузки,
- `SetupItem` — `ui/src/features/onboarding/plan.ts:7` — —
- `initialSelection` — `ui/src/features/onboarding/plan.ts:9` — —
- `toggled` — `ui/src/features/onboarding/plan.ts:14` — Обязательное снять нельзя: без него диалог не заработает.
- `downloadSize` — `ui/src/features/onboarding/plan.ts:27` — Сколько байт ещё скачивать: уже стоящее не считается.
- `canInstall` — `ui/src/features/onboarding/plan.ts:33` — —
- `formatSize` — `ui/src/features/onboarding/plan.ts:41` — —
- `percent` — `ui/src/features/onboarding/plan.ts:48` — —
- `parseAvatars` — `ui/src/features/onboarding/plan.ts:53` — Список аватаров из `avatars/index.json`; файла нет или он не JSON — только встроенный.
- `loadAvatars` — `ui/src/features/onboarding/plan.ts:62` — Dev-сервер на отсутствующий файл отдаёт index.html: такой ответ — тоже «файла нет».
- `restartApp` — `ui/src/features/onboarding/restart.ts:7` — Модели подхватываются при старте ядра, поэтому после установки приложение перезапускается.

## ui/src/features/privacy
Публичный API приватного режима (R-63).

- `PrivacyControl.svelte` — `ui/src/features/privacy/PrivacyControl.svelte:1` — Приватный режим и очистка памяти (S-17.2). Режим хранит ядро, поэтому индикатор честен и после

## ui/src/features/resources
Публичный API фичи ресурсов: панель и её горячая клавиша (R-63).

- `HISTORY_POINTS` — `ui/src/features/resources/history.ts:8` — Снимок приходит раз в секунду: на графике пять минут.
- `LoadHistory` — `ui/src/features/resources/history.ts:10` — —
- `addSnapshot` — `ui/src/features/resources/history.ts:17` — —
- `sparkline` — `ui/src/features/resources/history.ts:29` — Точки SVG `polyline`; новые — справа, вертикальный масштаб — от `maxMb`.
- `stateLabel` — `ui/src/features/resources/history.ts:52` — —
- `RESOURCES_HOTKEY_LABEL` — `ui/src/features/resources/index.ts:6` — —
- `isResourcesHotkey` — `ui/src/features/resources/index.ts:9` — По `code`, а не `key`: в русской раскладке `key` для этой клавиши — «Г».
- `ResourcesPanel.svelte` — `ui/src/features/resources/ResourcesPanel.svelte:1` — Панель ресурсов (FR-29): что сейчас в видеопамяти, кто и почему ждёт, нагрузка во времени.
