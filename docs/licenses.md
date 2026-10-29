# Лицензии компонентов

Проверено 2026-10-27. Не юридическая консультация: перед публикацией или монетизацией сверить
с актуальным текстом лицензий. Обновлять при выборе каждого компонента (ADR моделей, голоса,
аватара).

Статус: **проверено** — прочитан первоисточник по ссылке; **по памяти** — общеизвестная лицензия,
не перепроверялась в этой сессии.

## Главные ограничения

1. **Live2D — приложение-аватар требует отдельного соглашения.** Приложение, которое загружает
   произвольные модели (avatar system), по терминам Live2D — *Expandable Application*. Перед
   выпуском такого приложения нужны проверка и специальное соглашение о публикации; требование
   распространяется **на всех издателей, включая частных лиц и малый бизнес** (для них
   бесплатны только вступительный и ежегодный взносы; доля выручки — больше из $1.90 за продажу
   или 20 %). Полностью бесплатные Expandable Application, как правило, не одобряются, хотя
   исключения возможны. Разработка и пробный этап соглашения не требуют.
   → **Решено (ADR-0011): (а) личное использование без распространения.** Перед любым
   распространением — пересмотр: (б) соглашение с Live2D; (в) VRM (three-vrm, MIT); (г) одна
   фиксированная модель без загрузки сторонних. Cubism Core и модели в git не попадают —
   пользователь кладёт их сам (`ui/public/live2d/`, `ui/public/avatars/`).
2. **Silero TTS — некоммерческая лицензия** (CC BY-NC 4.0) для всех моделей, включая русские
   голоса (`xenia`, `baya`, `kseniya`, `aidar`, `eugene`). Исключение — базовые `cis-tts` модели
   под MIT. Коммерческое использование (монетизированные стримы) — только по договорённости
   с Silero. → **Решено (ADR-0014): голос по умолчанию — Silero `xenia`** (личное
   использование, как Live2D); публикация — пересмотр: CC0-голоса Piper русские только мужские
   (`denis`, `dmitri`), а персона — женская.
3. **Piper — лицензия зависит от голоса.** Русские: `denis`, `dmitri` — **CC0**; `ruslan` —
   CC BY-NC-SA 4.0; `irina` — лицензия датасета неизвестна. Сам движок: старый `rhasspy/piper`
   (MIT) архивирован 2025-10-06; разработка перенесена в `OHF-Voice/piper1-gpl` (судя по
   названию — GPL; проверить перед поставкой в составе приложения).

## Таблица

| Компонент | Назначение | Лицензия | Ограничения для нас | Статус |
|---|---|---|---|---|
| Live2D Cubism SDK / Core | рендер аватара | Live2D Proprietary Software License + SDK Release License | Expandable Application: проверка и соглашение для всех издателей; без соглашения — только разработка/личное использование | проверено |
| Live2D образцовые модели | разработка | Free Material License | коммерческое использование для малых издателей, кроме Unity-chan и Hatsune Miku | проверено |
| Модель витюбера | аватар | зависит от автора/покупки | права на конкретную модель — отдельно | не выбрана |
| Образцовая модель Haru (Live2D Inc.) | аватар для разработки | Free Material License (Live2D original character) | частным лицам и малому бизнесу — с согласием на условия; не в git | проверено (ReadMe в архиве) |
| untitled-pixi-live2d-engine 1.4 | Live2D для PixiJS 8 (ADR-0011) | MIT | — | проверено (npm) |
| Cubism Web Framework (внутри движка) | загрузка и анимация моделей | Live2D Open Software License | вместе с лицензией Core | по документации |
| Cubism Core for Web 5.1 (SDK 5-r.4) | ядро Live2D | Live2D Proprietary Software License | не в git; пользователь скачивает сам | проверено |
| PixiJS 8 | рендер | MIT | — | проверено (npm) |
| @pixi/sound | звук моушенов (транзитивно, не используется) | MIT | — | по памяти |
| three.js, @pixiv/three-vrm | VRM (альтернатива) | MIT | — | по памяти |
| Silero TTS (ru v3/v4/v5, выбрана v5_6_ru — ADR-0012; голос по умолчанию `xenia` — ADR-0014) | TTS | CC BY-NC 4.0 | некоммерческая; модель не в git | проверено |
| PyTorch (CPU), NumPy | движок Silero | BSD-3-Clause | — | по памяти |
| Silero TTS `cis-tts` base | TTS | MIT | — | проверено |
| Silero VAD | VAD | MIT | — | по памяти |
| Piper `ru_RU-denis`, `ru_RU-dmitri` (выбран denis-medium — ADR-0013; запасной — ADR-0014) | TTS | CC0 | голос не в git; мужские голоса | проверено |
| Piper `ru_RU-ruslan` | TTS | CC BY-NC-SA 4.0 | некоммерческая, share-alike | проверено |
| Piper `ru_RU-irina` | TTS | неизвестна (датасет RHVoice) | не использовать при публикации | проверено |
| Piper (движок) `piper-tts` 1.8 (`piper1-gpl`, ADR-0013) | TTS | GPL-3.0-or-later | копилефт при распространении; приложение не распространяется | проверено (PyPI) |
| onnxruntime | движок Piper | MIT | — | по памяти |
| XTTS-v2 | TTS (опция) | Coqui Public Model License | некоммерческая | по памяти |
| F5-TTS | TTS (опция) | код MIT, веса CC BY-NC | некоммерческие веса | по памяти |
| faster-whisper, веса Whisper | STT | MIT | — | по памяти |
| multilingual-e5-small (ONNX, ADR-0015) | эмбеддинги памяти | MIT | модель не в git | проверено (карточка HF) |
| sqlite-vec 0.1.9 (ADR-0015) | векторный поиск в SQLite | MIT / Apache-2.0 | — | по памяти |
| tokenizers, huggingface-hub (ADR-0015) | токенизатор e5 | Apache-2.0 | сеть не используется | по памяти |
| GigaAM | STT (альтернатива) | MIT | — | по памяти |
| multilingual-e5-small, bge-m3 | эмбеддинги | MIT | — | по памяти |
| sqlite-vec | векторное хранилище | MIT / Apache 2.0 | — | по памяти |
| llama.cpp | LLM-рантайм | MIT | — | по памяти |
| Tauri 2 | UI-оболочка | MIT / Apache 2.0 | — | по памяти |
| Svelte 5, Vite | UI | MIT | — | по памяти |
| LLM (выбирается в S-2.5) | мозг | своя у каждой модели (Apache 2.0, Llama Community, Gemma Terms…) | заполнить в ADR-0004 | не выбрана |

## Источники

- Live2D, Expandable Application: https://www.live2d.com/en/sdk/license/expandable/
- Live2D, справка по лицензиям SDK: https://help.live2d.com/en/other/other_14/
- Silero models (раздел лицензии в README): https://github.com/snakers4/silero-models
- Piper voices, MODEL_CARD: https://huggingface.co/rhasspy/piper-voices/tree/main/ru/ru_RU
- Piper (архив, переезд): https://github.com/rhasspy/piper
