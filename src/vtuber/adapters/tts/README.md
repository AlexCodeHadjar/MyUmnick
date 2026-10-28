# adapters/tts — адаптеры синтеза речи (TTSPort)

## Ответственность
Реализации `TTSPort` для конкретных движков: фраза → PCM s16le в объявленном формате. Переводят
исключения движка в доменные (R-43). НЕ нормализуют текст (`application/speech` — до TTS), не
режут поток на фразы, не знают о UI и протоколе; не импортируют application и gateway.

## Публичный API (`__init__.py`)
| Символ | Назначение |
|---|---|
| `PiperConfig` | Подсекция `[tts.piper]`: `model_path` (`.onnx`, рядом `.onnx.json`), `sample_rate` (сверяется с голосом), `length_scale`, `chunk_ms` |
| `PiperTTS(cfg, loader=)` | Piper (`piper-tts`, ADR-0013); голос грузится и прогревается в `async with` |
| `load_voice(path)`, `PiperVoiceLike` | Загрузка голоса; узкий протокол вместо API пакета |
| `SileroConfig` | Подсекция `[tts.silero]`: `model_path`, `speaker`, `sample_rate` (8/24/48 кГц), `threads`, `chunk_ms` |
| `SileroTTS(cfg, loader=)` | Silero v5.6 (ADR-0012); `async with` грузит модель один раз (R-40) |
| `load_package(path)` | Модель из `.pt`-пакета Silero через `torch.package` |
| `to_pcm(tensor)` | float [-1, 1] → s16le с обрезкой за шкалой |
| `SileroModel` | Протокол модели: `apply_tts(text=, speaker=, sample_rate=)` |

## Зависимости
- Порт `TTSPort`; domain: `AudioChunk`, `AudioFormat`, `TTSUnavailable`, `GenerationFailed`.
- Внешние: `torch` (CPU) и `numpy` — группа `silero`; `piper-tts` (+ `onnxruntime`) — группа
  `piper` (`uv sync --all-extras`). Пакеты движков импортируются только при загрузке модели.

## События
- Публикует: —
- Слушает: —

## Инварианты (контракт `tests/contract/test_tts_contract.py`, случаи `silero`, `piper` — `-m slow`)
- Модели нет или она битая — старт не падает, синтез бросает `TTSUnavailable` с подсказкой,
  откуда скачать (статус TTS виден в UI, как у LLM).
- Модель прогревается при загрузке (T-06): первый синтез у ONNX Runtime ~1.5 с.
- Синтез — в потоке (`asyncio.to_thread`), модель под блокировкой потоков: отменённый синтез
  дорабатывает в фоне и не сталкивается со следующим.
- Между фрагментами — уступка цикла: отмена срабатывает между фрагментами (T-14).
- Фраза без букв — без звука; ошибка движка посреди фразы — `GenerationFailed`.

## Производительность
- Горячий путь: да. Silero, машина разработки (12 ядер), 4 потока, после прогрева: 48 кГц — RTF p50
  0.035 / p95 0.048, первый фрагмент p50 86 мс / p95 166 мс; 24 кГц — RTF p50 0.052, первый
  фрагмент p50 137 мс. Цель Этапа 7 — RTF ≤ 0.3. Загрузка модели — 2.5 с (один раз).
- `bench/prompts_ru.jsonl` (40 промптов, текст нормализован; фраза = весь промпт, без нарезки):
  Silero xenia 48 кГц — RTF p50 0.041 / p95 0.151, первый фрагмент p50 145 мс; Piper denis
  22.05 кГц — RTF p50 0.184 / p95 0.322 / max 0.350, первый фрагмент p50 594 мс / p95 2059 мс.
- Silero не стримит внутри фразы: первый фрагмент = синтез всей фразы — поэтому первая фраза
  короткая (T-02).

## Как расширять
- Новый движок: файл в `adapters/tts/`, `TTSCase` в `tests/contract/factories.py` (рабочий и
  недоступный вариант, метки `slow`/`skipif` при тяжёлой модели), карточка здесь; регистрация в
  реестре bootstrap — с S-7.5.

## Связанные документы
ADR-0012, ADR-0013, T-02, T-06, T-11, T-14, `docs/licenses.md` (Silero — CC BY-NC 4.0, Piper — GPL-3.0, голос denis — CC0)
