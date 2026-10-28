# STATE — снимок проекта
_Обновлено: 2026-10-28, сессия S-7.5_

## Сейчас
- Этап: 7 — Голос (docs/stages/STAGE_07.md). Этап 6 закрыт (веха M2: чат слева, живая модель
  справа).
- Следующая сессия: **S-7.6 — аудиоплеер и липсинк в UI** (docs/stages/STAGE_07.md): ядро уже
  шлёт звук бинарными кадрами (`serve`, движок `[tts].backend`, по умолчанию Silero). Аватар: Haru в
  `ui/public/avatars/haru/` (+ наш `mapping.json` в git), Core 5.1 (SDK 5-r.4) в
  `ui/public/live2d/` — вне git.
- **Отложено до целевой машины (RTX 5070 Ti):** S-2.5 (выбор модели, ADR-0004), прогоны `-m gpu`,
  ручная проверка M1 (`uv run python -m vtuber` с реальной моделью). Вместо своей машины —
  аренда 5070 Ti на gpu.nz: всё готово в `scripts/remote/` (README — порядок действий, 5
  кандидатов × Q4/Q5 в `models.tsv`, ключ `~/.ssh/gpunz_ed25519`). Ждёт пополнения и запуска
  сервера пользователем.
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

## Последние метрики
- TTFA ядра (`tts.first_audio`, FakeLLM ~50 ток/с, машина разработки): Silero p50 231 мс (max
  347), Piper p50 237 мс. Плюс сеть и плеер UI — S-7.6; плюс настоящий TTFT — целевая машина.
- TTS на `bench/prompts_ru.jsonl` (целые промпты): Silero 48 кГц — RTF p50 0.041 / p95 0.151, первый
  фрагмент p50 145 мс; Piper denis — RTF p50 0.184 / p95 0.322, первый фрагмент p50 594 мс.
- Silero v5_6_ru (машина разработки, 4 потока): 48 кГц — RTF p50 0.035 / p95 0.048, первый
  фрагмент p50 86 мс; 24 кГц — RTF p50 0.052, 137 мс. Загрузка модели 2.5 с.
- `span()`: ≈ 1.2–1.5 мкс на замер (машина разработки).
- TTFT/TPS настоящей модели — ещё нет (S-2.5).
- Аватар Haru (окно Tauri, 146 Гц): стриминг — 140 к/с, медиана кадра 6.9 мс, p99 7.2 мс.
- UI (окно Tauri, фейковое ядро): Enter → первый символ 2–14 мс; прокрутка 1000 сообщений —
  медиана кадра 6,9 мс, p95 9 мс; в DOM 17–22 строки.

## Открытые проблемы
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
- Голос только в `serve`; в тестах шлюза — `VTUBER_TTS__BACKEND=none`, иначе грузится Silero.
  Сквозной тест звука — `uv run pytest -m slow tests/integration/test_serve_app.py`.
- Окружение — `uv sync --all-extras`: без группы `silero` нет torch, и mypy/тесты Silero упадут.
  Контракт Silero — `uv run pytest -m slow tests/contract/test_tts_contract.py`.
- Скрипты `tools/` запускаются модулем: `uv run python -m tools.<имя>` (`python tools/x.py` не
  видит пакет `tools` и падает на импорте).
- Аватар: модель — `VITE_AVATAR`, всё модель-зависимое — `ui/public/avatars/<имя>/mapping.json`
  (`ui/README.md`). Dev-сервер Vite на отсутствующий файл отдаёт index.html с кодом 200 —
  загрузчики считают не-JSON отсутствием файла.
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
- Протокол меняется только в `gateway/protocol.py`; сообщение добавляется вместе с кодом,
  который его использует. JSON — pydantic-core, orjson не нужен.
- Новая зависимость — ADR. ADR-0004 — выбор LLM (S-2.5); следующий свободный — ADR-0014.

## Последний журнал
docs/ai/sessions/2026-10-28_S-7.5.md
