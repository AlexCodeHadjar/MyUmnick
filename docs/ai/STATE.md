# STATE — снимок проекта
_Обновлено: 2026-11-03, сессия S-14.3_

## Сейчас
- **Сборку готового проекта (S-13.3, PyInstaller, установщик) не запускать до команды пользователя**; этапы ещё
  будут добавляться. Этап 12: остались S-12.5 и S-12.6, ждут аренды. Пользователь попросил сделать все этапы подряд. Без решения пользователя дальше нельзя: движок S-18.5 ждёт выбора голоса (Этап 19). S-12.5 и
  S-12.6 ждут аренды (выбор модели для кода). Этап 13 от этапов 14–16 не зависит.
- Этап 11 готов по коду (S-11.1…S-11.3, ADR-0016): микрофон вживую, `voice.end_to_audio` и ложные
  перебивания не проверены. Этапы 7, 8 и 10 закрыты по коду; модель выбрана
  (ADR-0004), замеры на аренде — `docs/perf/gpu-run-2026-11-02.md`.
- **Нужна следующая аренда 5070 Ti** (сервер gpu.nz остановлен по просьбе пользователя; диск платный,
  удаление за ним): `scripts/remote/finish_chosen.sh` — eval на 150 кейсах (S-10.6), сквозная память,
  цена памяти в TTFT (+≤ 40 мс), влияние grammar на TTFT; затем S-9.1 (профилирование), S-9.3.
- **Этап 19, голос по образцу:** S-19.1 готова к аренде (`scripts/remote/clone_voice.sh`, образцы вне git —
  `data/voice_refs/silv/`, разрешение автора голоса подтвердил пользователь 2026-11-03); движки не запускались.
- **За пользователем:** оценка русского 1–5 (ADR-0004), выбор голоса (ADR-0014, образцы —
  `bench/results/tts_samples/index.html`), проверка текста образцов (`data/voice_refs/silv/prepared/refs.json`),
  ручная проверка M1 и удаление сервера.
- Аватар: Haru в `ui/public/avatars/haru/` (+ наш `mapping.json` в git), Core 5.1 (SDK 5-r.4) в
  `ui/public/live2d/` — вне git.
- Ветка: `main`. Удалённого репозитория нет: push невозможен до настройки remote пользователем.
- Режим: пользователь разрешил идти по сессиям без подтверждения и коммитить сразу.

## Готово
- [x] Этапы 0, 1; Этап 2 — S-2.1…S-2.4 (кроме прогонов на целевой машине)
- [x] Этап 3 — S-3.1…S-3.5: персона, промпт, память, разбор, конвейер, сервис хода, терминальный
  чат, сборка в bootstrap (кроме ручной проверки M1 с реальной моделью)
- [x] S-4.1 Протокол v1 (`gateway/protocol.py`) и кодек (JSON + бинарный аудиокадр)
- [x] S-4.2 WebSocket-шлюз (`python -m vtuber serve`), `WsReplySink`, ADR-0008
- [x] S-4.3 `tools/gen_protocol.py` → `ui/src/core/protocol.gen.ts`, `docs/protocol.md`
- [x] S-5.1 Каркас `ui/` (Tauri 2 + Svelte 5 + TS 6.0 + Vite 8, pnpm), хуки и CI-job `ui`,
  ADR-0009; `pnpm tauri dev` открывает окно
- [x] S-5.2 `ui/src/core/`: `CoreClient`, транспорт (переподключение, очередь, код 4000), разбор
  кадров, `AppStore` на рунах; vitest (ADR-0010)
- [x] S-5.3 `ui/src/features/chat/`: виртуализированная история, ввод, «Стоп», «печатает»;
  батч входящих на rAF (`core/batch.ts`)
- [x] S-5.4 Раскладка с разделителем (доля в localStorage), статус-бар, панель метрик
  (Ctrl+Shift+M, замер UI `ui.first_char`), раздел `ui/src` в карте (`tools/ui_map.py`)
- [x] S-6.1 ADR-0011 (PixiJS 8 + untitled-pixi-live2d-engine 1.4 + Cubism Core 5; лицензия —
  личное использование), контракт `AvatarRenderer`
- [x] S-6.2 `Live2DRenderer`, `AvatarLoop` (кадры вне Svelte, пауза при скрытом окне), `AvatarSession`,
  `AvatarStage`; Pixi и движок — динамический чанк; Haru в окне, 140 к/с при стриминге
- [x] S-6.3 `mapping.json` (выражения, эмоции, реакции, кадр) с проверкой; «думаю» в кадре
  отправки (T-17); маппинг Haru — кадр «по пояс»
- [x] S-7.1 `TTSPort` (`audio_format`, `synthesize` → `AsyncGenerator[AudioChunk]`), `FakeTTS(rtf)`,
  контракт `tests/contract/test_tts_contract.py` (`TTSCase`)
- [x] S-7.2 `SentenceChunker` (+ `ChunkerConfig`, секция `[pipeline.chunker]` — в default.toml с
  S-7.5), `application/speech`: `normalize_for_speech`, числа, латиница
- [x] S-7.3 `SileroTTS` (v5_6_ru, torch CPU — группа `silero`, ADR-0012); контракт TTSPort для Silero
  (`-m slow`); модель — `models/tts/silero/v5_6_ru.pt`, вне git
- [x] S-7.4 `PiperTTS` (piper-tts 1.8, голос denis CC0 — группа `piper`, ADR-0013); прогрев при
  загрузке у обоих движков (T-06); контракт для Piper (`-m slow`)
- [x] S-7.5 TTS-ветка конвейера (`Speaker`, `Voice`), `ReplySink.audio`, бинарные кадры в
  `WsReplySink`, секции `[tts]` и `[pipeline.chunker]`, реестр `tts_backends()`, загрузка голоса
  со статусом TTS в UI
- [x] S-7.6 `ui/src/features/audio/`: `VoicePlayer` (AudioWorklet, fade 128 сэмплов, ресемплинг),
  липсинк по звучащему сигналу → `setMouth`; новый ход вытесняет звук прошлого, стоп/новая
  реплика/Esc глушат сразу; замер `ui.first_audio` (норма 800)
- [x] S-7.7 `tools/bench_voice.py` (TTFA, «TTFA − TTFT», RTF фраз, паузы; `--simulate-llm`),
  ADR-0014: голос по умолчанию — Silero `xenia` 48 кГц, Piper `denis` — запасной; `audio.played`
  — вместе с состоянием «говорит»
- [x] S-8.2 «Говорит» от плеера (`store.voice.speech`); эмоция с затуханием (`mood.ts`, 4 с + 1,5 с),
  кивок на `turn.started` (`nod.ts`), «думаю» после 800 мс без ответа, моргание чаще в речи,
  «Стоп» до конца звука, режим субтитров (`chat/subtitles.ts`)
- [x] S-8.3 Междометия-заглушки (`pipeline/filler.py`: `FillerBank`, `AudioOut`; секция
  `[pipeline.filler]`): «Хм…/Так…/Сейчас…», если звука ответа нет через 1000 мс; синтез при
  загрузке голоса; ответ не накладывается
- [x] S-9.2 Speculative prefill: `input.typing` (протокол), `ConversationService.typing` (прогрев
  историей + черновиком между ходами, отмена устаревшего), `ReplyPipeline.prefill` (замер
  `llm.prefill`), UI — черновик через 300 мс паузы (`chat/typing.ts`); `bench_latency
  --speculative` для замера T-05
- [x] S-10.1 Порты памяти: `EmbedderPort`, `MemoryStorePort` (`ports/memory.py`), домен `Fact`,
  `FactHit`, `FactSource`, `Vector`, `EmbedKind`, `MemoryUnavailable`; фейки `FakeEmbedder`
  (хэш триграмм), `FakeMemoryStore`; контракты в `tests/contract/` (`memory_factories.py`)
- [x] S-10.2 `adapters/memory`: `E5Embedder` (multilingual-e5-small ONNX на CPU), `SqliteVecStore`
  (факты + vec0, косинус); группа `memory` (ADR-0015); модель — `models/memory/e5-small/`, вне git
- [x] S-10.3 `application/scheduler`: `IdleScheduler` (фон по одной задаче после `idle_after_ms`,
  `busy()` отменяет сразу, отменённая повторяется), `follow(bus)`
- [x] S-10.4 Фоновая память: `Summarizer` (резюме отрезанного — в первой реплике истории),
  `FactExtractor` (строгий JSON), `FactMemory` (дедупликация по смыслу), `MemoryKeeper` (задачи
  простоя по `TurnRemembered`); `bootstrap/memory.py` — слот LLM 1, e5, sqlite-vec, планировщик;
  секции `[memory]`, `[scheduler]`; база — `data/memory.sqlite`
- [x] S-2.5 Модель: Gemma 4 12B HauhauCS Balanced Q4 (ADR-0004); S-8.1 теги эмоций 96 %
  (`tools.eval_emotion`, записанные ответы в тестах); замер S-9.2: −34…−43 % TTFT длинных реплик
- [x] S-11.1…S-11.3 Микрофон, `VadPort`/`STTPort`, Whisper turbo + Silero VAD (модели — `models/stt/`, грузятся
  при первом кадре), `application/voice`, `gateway/voice_bridge.py`, перебивание; секция `[stt]`
- [x] S-10.5 Гейт поиска и справка из фактов (`retrieval_gate.py`, `[memory.retrieval]`)
- [x] S-10.6 Наборы: `eval/qa_ru.jsonl` 150 кейсов, `eval/memory_ru.jsonl`; `tools.eval_memory`,
  `tools.bench_memory`; `forbid_foreign_scripts` (grammar). Отчёт качества — при следующей аренде
- [x] S-12.1 `kernel/plugin.py` (`Plugin`, `PluginContext`, `PluginsConfig`), `bootstrap/plugins.py`,
  `plugins/example/`, `docs/plugins.md`, секция `[plugins]`
- [x] S-12.2 `MessageSource`, `PluginContext.add_source`, `gateway/external_turns.py`,
  `ConversationService.wait_silent`, `plugins/stream_chat/` (Twitch анонимно, фильтры, очередь, лимит)
- [x] S-12.3 `plugins/obs/` (OBS WebSocket 5), события `PhraseVoiced` и `EmotionChanged` на шине
- [x] S-12.4 `application/tools`, `PluginContext.add_context`, `plugins/tools/` (время, таймер, заметки);
  внешние реплики без инструментов и фактов (`handle(..., external=True)`)
- [x] S-12.7 `ResourceManager` (`application/scheduler/resources.py`), порт `ManagedModel`, секция `[resources]`,
  ADR-0017; моделей под управлением пока нет
- [x] S-12.8 `plugins/stream_director/`, `PluginContext.add_command`, события канала Twitch (рейд, подписка)
- [x] S-12.9 Лимит по фактической VRAM: `GpuProbe`, `adapters/gpu` (`nvidia-smi`, ADR-0018), `max_tool_mb`,
  `max_background_mb`
- [x] S-12.10 Панель ресурсов (Ctrl+Shift+U): `ui/src/features/resources/`, `resources.watch`, `resources.snapshot`,
  `gateway/resources_feed.py`
- [x] S-13.1 Сборка ядра PyInstaller (`packaging/`, ADR-0019), `LlamaServerProcess`, `[llama_server]`, запуск ядра окном
- [x] S-13.2 Мастер: `application/setup`, `adapters/setup`, `gateway/setup_bridge.py`, `config/catalog.toml`,
  `ui/src/features/onboarding/`; выбор — в `config/setup.toml`
- [x] S-12.11 `domain/viewer.py`, подпись реплик зрителей, блокировка явных атак, счётчик в строке статуса, зрители
  вне резюме и фактов; набор `eval/viewer_attacks_ru.jsonl`, `tools.eval_viewer_attacks`
- [x] S-16.4 Память в Markdown (`adapters/memory/obsidian_vault.py`, `note_format.py`, `application/memory/vault_sync.py`,
  ADR-0020): факты, чаты, резюме, пересборка индекса, импорт; разговор возвращается при запуске
- [x] S-16.5 Правки заметок на ходу: `VaultWatcher`, сверка по заметкам (`reconcile`), `changes_token`, `scan`
- [x] S-17.1 Самовосстановление: `application/supervision`, `bootstrap/supervision.py`, `backend.notice`, Job Object для
  llama-server, ADR-0021; проверено на заглушке вместо llama-server
- [x] S-17.2 Приватный режим и очистка памяти: `Turn.is_private`, `MemoryEraser`, `gateway/privacy_bridge.py`,
  `ui/src/features/privacy/`
- [x] S-16.2 Редактор памяти: `MemoryEditor`, `gateway/memory_bridge.py`, `ui/src/features/memory/` (Ctrl+Shift+Y), `[memory].profile`
- [x] S-16.1 Ветвление: `application/conversation/branches.py`, `gateway/branch_bridge.py`, `chat/BranchBar.svelte`
- [ ] S-18.5 Пение: `plugins/singing` исполняет готовую запись, движок не выбран (ADR-0028)
- [x] S-14.3 Собеседники: отпечаток на фразу, `application/voice/speakers.py`, `[stt.speakers]` выключено; ошибки на людях ждут записи (ADR-0029)
- [x] S-14.4 Звуки: `application/voice/sounds.py`, `adapters/stt/sensevoice.py`, `[stt.sounds]` выключено; точность ждёт записей, `tools.eval_sounds` (ADR-0027)
- [x] S-14.1, S-14.2 Слух по тексту Whisper: `[stt.addressing]`, `unfinished_hold_ms`, ADR-0026; замеры ждут записей
- [x] S-18.2 Снимок экрана: `features/chat/screen.ts`, только по действию, ADR-0025; выбор окна вживую не проверен
- [x] S-18.1 Картинка от пользователя: `Message.images`, `chat.send_image`, `[llama_server].mmproj`, ADR-0024; замеры ждут аренды
- [x] S-18.3 Липсинк по спектру: `features/audio/viseme.ts`, `mapping.json` → `lipsync`, ADR-0023; на настоящем голосе не проверено
- [x] S-18.4 Жесты: `Gesture`, `GestureCue`, `avatar.gesture`, `mapping.json` → `gestures`, `tools/eval_gesture.py`; замер ждёт модели
- [x] S-15.2 Поверх стола: `ui/src/features/desktop/`, прозрачное окно, клики сквозь пустоту; вживую не проверено
- [x] S-15.1 Инициативные реплики: `application/conversation/initiative.py`, `[initiative]` (выключено), `window.visibility`
- [x] S-16.3 Поиск: `plugins/web_search/` (локальный SearXNG), `ContextTool` со своим сроком, `chat.sources`, ADR-0022

## Последние метрики
- Сборка ядра: 659 МБ, 233 с; старт до готовности голоса 7–10 с, самый первый 41.7 с (без сборки 11–13 с).
- Память (машина разработки): запрос e5 5.4 мс; поиск топ-5 p95 3.5 мс / 2000 фактов, 11.9 мс /
  10 000; e5 + поиск p95 9.5 / 17.7 мс (бюджет 40 мс).
- TTFA бенчмарка (`tools.bench_voice --simulate-llm`, TTFT 250 мс, 40 ток/с, 40 реплик): Silero
  p50 516–545 мс, p95 ≤ 615; Piper p50 550; при 80 ток/с — 430–440. «TTFA − TTFT» p50 ≈ 250 мс
  (40 ток/с) / 157 мс (80 ток/с): в основном ожидание первой фразы. RTF фраз p95 ≤ 0.08, пауз
  сверх звука нет.
- TTFA в окне (`ui.first_audio`, Enter → звук; заглушка LLM ~50 ток/с, Silero 48 кГц): p50 160 мс,
  p95 178 мс; отмена — тишина через 32 мс («Стоп»), 84 мс (Esc после конца хода). Плюс настоящий
  TTFT — целевая машина.
- TTFA ядра (`tts.first_audio`, FakeLLM ~50 ток/с, машина разработки): Silero p50 231 мс (max
  347), Piper p50 237 мс.
- TTS на `bench/prompts_ru.jsonl` (целые промпты): Silero 48 кГц — RTF p50 0.041 / p95 0.151, первый
  фрагмент p50 145 мс; Piper denis — RTF p50 0.184 / p95 0.322, первый фрагмент p50 594 мс.
- Silero v5_6_ru (машина разработки, 4 потока): 48 кГц — RTF p50 0.035 / p95 0.048, первый
  фрагмент p50 86 мс; 24 кГц — RTF p50 0.052, 137 мс. Загрузка модели 2.5 с.
- `span()`: ≈ 1.2–1.5 мкс на замер (машина разработки).
- Настоящая модель (RTX 5070 Ti, сервер): TTFT p50 59–65 / p95 130–144 мс, TPS 89; TTFA p50 256 / p95
  451 мс; RTF Silero 0.024, пауз нет; подробно — `docs/perf/gpu-run-2026-11-02.md`.
- Аватар Haru (окно Tauri, 146 Гц): стриминг — 140 к/с, медиана кадра 6.9 мс, p99 7.2 мс.
- UI (окно Tauri, фейковое ядро): Enter → первый символ 2–14 мс; прокрутка 1000 сообщений —
  медиана кадра 6,9 мс, p95 9 мс; в DOM 17–22 строки.

## Открытые проблемы
- [P2] Мастер не проверен в окне Tauri: перезапуск `restart_app` и запуск ядра только компилируются. Сборка
  отложена. В S-13.3 сгенерировать `avatars/index.json` и пересобрать ядро: мастер в прошлой сборке отсутствует.
- [P1] `llama-server.exe` `b12064` запускался только с `--version` и `--help` (остальное запретила система
  разрешений): `--list-devices` и работа с моделью не проверены. Запуск ядра окном (`lib.rs`) прошёл только `cargo check`.
- [P3] OBS: не разобрано зависание проверочного скрипта при опросе OBS, перезапущенного посреди работы `serve`
  (сам диалог работал; переподключение отдельно подтверждено). Глазами в эфире субтитры не смотрели.
- [P2] Защита стрима (S-12.11): правила обходятся перефразированием; как настоящая модель держит подписанный
  текст зрителя, не проверено: `uv run python -m tools.eval_viewer_attacks --llm` при аренде.
- [P2] TTFT с инструментом на настоящей модели не замерен (S-12.4): нужна аренда.
- [P2] YouTube в `plugins/stream_chat` нет; плагин не проверен на настоящем канале Twitch.
- [P1] Speculative prefill (S-9.2) не измерен: нужен настоящий llama-server — сравнить
  `tools.bench_latency` и `--speculative` на репликах > 15 слов (цель −30 % TTFT). Не проверено,
  ждёт ли настоящий запрос чата незаконченный прогрев в том же слоте.
- [P1] Не проверено на настоящем llama-server (целевая машина): `scripts/start_llm.ps1`,
  `uv run pytest -m gpu`, `n_ctx` на слот, поля `id_slot`/`chat_template_kwargs` в чате; бенчмарк
  и eval против реальной модели; S-2.5; ручная проверка M1.
- [P2] Движок Live2D 1.4 не работает с Cubism Core 6 (SDK 5-r.5) — держим Core 5.1 из SDK 5-r.4
  (issue #11 движка). Загрузчик отказывает Core ≥ 6 с подсказкой.
- [P1] Лицензия Live2D (ADR-0011): только личное использование. Любое распространение
  приложения — сначала пересмотр ADR (соглашение с Live2D / одна модель / VRM).
- [P2] Голоса: Silero — CC BY-NC; коммерчески чистые русские — Piper `denis`/`dmitri` (CC0).
- [P2] `chars_per_token = 3.0` — оценка «на глаз»; откалибровать по `/tokenize` (S-9.1).
- [P3] Резюме отрезанной истории не делается: отрезанное просто теряется до Этапа 10.
- [P3] Бенчмарк и eval (`tools/llm_client.py`) — со своим временным системным промптом; перевести
  на `render_system_prompt(load_persona(...))`.
- [P3] Ctrl+C в терминальном чате завершает приложение целиком (прервать ответ — новой строкой
  или `/stop`).
- [P3] Piper: RTF p95 0.322 (> 0.3) и первый фрагмент p50 594 мс на целых промптах — синтез
  всей фразы до первого фрагмента. Если Piper станет основным — отдавать по предложениям из
  потока (`synthesize` пакета стримит по предложениям).
- [P3] Нормализатор не склоняет числа после предлогов («в 2024 году» → «в две тысячи двадцать
  четыре году») и не делает порядковые; кириллические аббревиатуры («ГБ», «км») не
  раскрываются. Решать, если голос будет звучать плохо.
- [P3] Ядро не знает, что голос ещё звучит (`audio.played` не реализован, ADR-0014): «говорит» —
  только в UI (`store.voice`). Понадобится ядру (например, не перебивать речь своей репликой на
  Этапе 9) — добавить сообщение в протокол.
- [P3] Субтитры — по доле звука, а не по словам: протокол не связывает текст со временем звука.
  Точная привязка — отметки фраз в кадрах звука (изменение протокола).
- [P2] Междометия звучат одинаково для любой реплики и не проверены на слух («Хм…» у Silero —
  0.53 с звука, у Piper — 0.65 с). Если звучат плохо — поменять `phrases` в конфиге.
- [P3] Междометие сдвигает ответ: ответ, готовый во время «Хм…», ждёт его конца (до ~0.8 с).
  Поэтому срок 1000 мс — выше бюджета TTFA: обычный ответ междометия не получает.
- [P2] Извлечение фактов и резюме не проверены на настоящей модели (промпты подобраны без неё):
  `tools.eval_memory` при следующей аренде. Векторы e5 не отличают противоречие от повтора
  («живёт в Москве» / «в Казани» — 0.96): `dedup_score = 0.97`, новый факт не заменяет старый.
- [P3] Фоновая память грузит e5 до открытия шлюза (+~1 с к старту `serve`); набор текста не
  считается «занято» для планировщика (фон может идти, пока пользователь печатает).
- [P3] Частота моргания в речи не замерена (вызов `eyeBlink.setBlinkingInterval` проверен
  перехватом, сами моргания — нет).
- [P2] Качество голосов в ADR-0014 — предварительная оценка, не на слух: пользователю
  послушать `xenia`/`baya`/`kseniya` и `denis` и поправить таблицу.
- [P3] Щелчки на стыках проверены тестами fade и замером, не на слух; Piper (22 050 Гц) в окне
  не слушали.
- [P3] Покрытие UI-тестов не считается (нет `@vitest/coverage-v8`, ADR-0010).
- [P3] Компоненты Svelte не тестируются автоматически (нет jsdom/браузерного режима vitest):
  логика вынесена в `.ts` и покрыта, DOM проверен вручную через CDP. Фейковое ядро и скрипты
  CDP-замеров — вне репозитория (временная папка); перенести в `tools/` с тестами, если понадобятся
  регулярно.
- [P3] Реестр LLM типизирован базовым `OpenAICompatLLM`; не-HTTP адаптеру понадобится протокол
  «LLMPort + async-контекст».
- [P3] Текст ошибок pydantic в `ConfigError` — на английском.
- [P3] `tools/gen_map.py` не показывает модульные константы и `type`/`NewType`-псевдонимы.
- [P3] R-06 (импорт в обход `__init__`) не автоматизирован — только ревью.
- [P3] Rust и Node не в PATH Git Bash: `~/.cargo/bin`, `C:\Program Files\nodejs`,
  `%APPDATA%\npm` (pnpm) — добавлять вручную.
- [P3] uv через `pip --user`: `C:\Users\Alast\AppData\Roaming\Python\Python312\Scripts` не в PATH.
- [P3] WebView2 на машине разработки стоит в профиле пользователя (`%LOCALAPPDATA%`, v156): Edge
  из системы вырезан, устаревшая запись HKLM удалена. Если окно снова не найдёт рантайм —
  `winget install -e --id Microsoft.EdgeWebView2Runtime`. Фронтенд без окна — предпросмотр
  `ui-vite` (`.claude/launch.json`, порт 1420).

## Важно помнить
- Сборка ставит плагины `obs`, `stream_chat`, `stream_director`, `tools` в `.venv`; `uv sync` их убирает. Каталог
  `packaging/` без `__init__.py`: имя совпадает с пакетом из PyPI, модулем скрипты не запускать.
- OBS для проверок: портативный 33.0.1 в `%LOCALAPPDATA%\obs-portable` (пароль WebSocket — в его
  `config/obs-studio/plugin_config/obs-websocket/config.json`); запуск `bin/64bit/obs64.exe --portable`.
- Голос только в `serve`; в тестах шлюза — `VTUBER_TTS__BACKEND=none`, иначе грузится Silero.
  Сквозной тест звука — `uv run pytest -m slow tests/integration/test_serve_app.py`.
- Бенчмарк голоса: `uv run python -m tools.bench_voice --tts silero [--simulate-llm]`; в консоли
  Windows с cp1251 — только ASCII в выводе (знак «−» роняет print).
- Окружение — `uv sync --all-extras`: без группы `silero` нет torch, и mypy/тесты Silero упадут;
  без группы `memory` — onnxruntime/tokenizers/sqlite-vec для памяти.
- Интеграционные тесты запуска (`test_serve_app`, `test_terminal_app`) — с
  `VTUBER_MEMORY__ENABLED=false`, иначе создадут `data/memory.sqlite` в корне; память целиком —
  `tests/integration/test_memory_app.py` (`-m slow`, база в `tmp_path`).
- Модель памяти: `models/memory/e5-small/{model.onnx,tokenizer.json,config.json}` из
  `huggingface.co/intfloat/multilingual-e5-small/tree/main/onnx` (ревизия `614241f`, ADR-0015);
  контракт e5 — `uv run pytest -m slow tests/contract/test_embedder_contract.py`.
  Контракт Silero — `uv run pytest -m slow tests/contract/test_tts_contract.py`.
- Скрипты `tools/` запускаются модулем: `uv run python -m tools.<имя>` (`python tools/x.py` не
  видит пакет `tools` и падает на импорте).
- Аватар: модель — `VITE_AVATAR`, всё модель-зависимое — `ui/public/avatars/<имя>/mapping.json`
  (`ui/README.md`). Dev-сервер Vite на отсутствующий файл отдаёт index.html с кодом 200 —
  загрузчики считают не-JSON отсутствием файла.
- Голос в UI: `connectVoice(client)` (`features/audio`); звук — мимо пачки кадра, отмена — сразу
  (`CoreClient.onCancel`). AudioContext стартует первым жестом; для CDP-проверок окно запускать с
  `--autoplay-policy=no-user-gesture-required` или кликать через `Input.dispatchMouseEvent`.
  Живая проверка: заглушка `tests/llm_stub.py` + `python -m vtuber serve` с
  `VTUBER_LLM__BASE_URL` (uv нет в PATH bash — `.venv/Scripts/python.exe`).
- Svelte 5: в `$effect` читать реактивное значение до `x?.` — `session?.mood.set(store.emotion)`
  при пустой сессии не читает `store.emotion`, и эффект не подписывается (баг S-8.2).
- Проверка вызовов рендера в окне: `import()` модуля по URL из
  `performance.getEntriesByType('resource')` (с `?t=` после HMR) и перехват методов прототипа.
- UI: фичи берут всё из `ui/src/core/index.ts` (`CoreClient`: `store`, `say`, `stop`); адрес ядра —
  `VITE_CORE_URL` в `ui/.env`. Входящие применяются к store раз в кадр (`FrameBatch`, T-16).
- Замеры UI — в окне Tauri, не в панели браузера Claude: скрытая панель почти не крутит
  `requestAnimationFrame`. Окно с CDP: `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS="--remote-debugging-port=9222"`
  перед `pnpm tauri dev`.
- Целевое железо: RTX 5070 Ti 16 ГБ VRAM, 32 ГБ RAM (Blackwell → llama.cpp с CUDA 12.8+).
- Запуск: `uv run python -m vtuber [chat|serve] [--root путь]`; коды 0 / 1 (конфиг) / 2 (LLM
  недоступна в чате). `serve` живёт, пока открыт stdin (sidecar Tauri).
- Логи — `kernel.logging_to` (без кэша логгеров): иначе логгеры модулей пишут в закрытый файл.
- Сервис хода владеет задачей хода; новая реплика отменяет и дожидается предыдущий; в истории —
  `full_text` с тегами, прерванное — с «…», реплика пользователя — без справки.
- Реестр LLM-адаптеров — `bootstrap.llm_backends()` (модульный изменяемый реестр нарушил бы R-04).
- `get_logger` — без `.bind()`: имя модуля идёт начальным значением ленивого прокси (иначе
  логгеры, взятые при импорте, писали в консоль мимо настроенного файла).
- `LLMPort.stream` → `AsyncGenerator[str]`; потребитель закрывает через `contextlib.aclosing`.
- `\u…` в параметрах инструментов записи раскрывается в символ — невидимые символы вписывать
  через `chr()`.
- Файлы — всегда `encoding="utf-8"`; `.ps1` — UTF-8 **с BOM**.
- Протокол меняется только в `gateway/protocol.py` и `protocol_extras.py`; сообщение добавляется вместе с кодом,
  который его использует. JSON — pydantic-core, orjson не нужен.
- Новая зависимость — ADR. ADR-0004 — выбор LLM (S-2.5); следующий свободный — ADR-0030.

## Последний журнал
docs/ai/sessions/2026-11-03_S-14.3.md
