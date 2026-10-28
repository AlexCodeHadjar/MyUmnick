# ADR-0013: второй движок TTS — Piper (piper-tts 1.8, голос denis, CC0), необязательная группа
- Статус: принято
- Дата: 2026-10-28

## Контекст
План Этапа 7 — два движка за одним `TTSPort` (S-7.3 Silero, S-7.4 Piper): Silero звучит лучше,
но модели под CC BY-NC 4.0; Piper — ONNX без torch, у русских голосов `denis` и `dmitri`
лицензия CC0 — путь на случай публикации или монетизации (`docs/licenses.md`).

## Рассмотренные варианты
Пакет движка (PyPI, 2026-10-28):
1. **`piper-tts` 1.8.0** (OHF-Voice/piper1-gpl, GPL-3.0-or-later; колесо `win_amd64`,
   зависимости — `onnxruntime`, `pathvalidate`; espeak-ng для фонем встроен) — поддерживаемая
   ветка, API `PiperVoice.load` / `synthesize` (поток фрагментов по предложениям).
2. Старый `rhasspy/piper` (MIT) — архивирован 2025-10-06.
3. Свой вызов ONNX через `onnxruntime` + фонемизатор — фонемы espeak-ng пришлось бы собирать
   самим; несоразмерно задаче.

Голос: `ru_RU-denis-medium` (CC0, 63 МБ) против `ru_RU-dmitri-medium` (CC0, тот же размер) —
равноценны; `irina` — лицензия неизвестна, `ruslan` — CC BY-NC-SA.

## Решение
- `piper-tts>=1.8,<2` — необязательная группа `piper` (как `silero`): ядро и Silero без него
  работают; полная установка — `uv sync --all-extras`.
- Голос — `models/tts/piper/ru_RU-denis-medium.onnx` + `.onnx.json` (вне git), с
  `huggingface.co/rhasspy/piper-voices` (`ru/ru_RU/denis/medium/`).
- **GPL:** приложение не распространяется (ADR-0011) — копилефт не срабатывает. Распространение
  сборки с `piper-tts` потребует GPL-совместимого лицензирования всего пакета или замены движка
  (вариант 3) — отметка в `docs/licenses.md`.
- Синтез — в потоке, под блокировкой, как у Silero; ONNX Runtime на CPU (T-11).

## Последствия
- `docs/licenses.md`: piper-tts — GPL-3.0-or-later; onnxruntime — MIT; голос denis — CC0.
- Контракт TTSPort для Piper — медленный случай (`-m slow`), пропуск без файлов голоса.
- Какой движок по умолчанию — решается в S-7.5 по замерам RTF и TTFA обоих.
