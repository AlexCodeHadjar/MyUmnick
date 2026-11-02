# ADR-0016: голосовой ввод — faster-whisper large-v3-turbo и Silero VAD
- Статус: принято
- Дата: 2026-11-02

## Контекст
Этап 11: разговор голосом; от конца фразы до первого звука ответа — ≤ 1.5 с p50. TTFA ответа уже
256 мс (`docs/perf/gpu-run-2026-11-02.md`), остаётся бюджет на паузу конца фразы (500–700 мс) и
распознавание. На видеокарте после LLM свободно ≈ 7 ГБ из 16.

## Рассмотренные варианты
Распознавание (план `docs/stack.md`): faster-whisper против Vosk (быстро, но хуже качество) и
GigaAM (сильный русский, но другой стек и нет готового выбора языка).

Модель Whisper (выбрал пользователь, 2026-11-02): **large-v3-turbo** (1.6 ГБ, лучшее качество на
русском, рассчитана на GPU) против `small` (484 МБ, для CPU) и `base` (145 МБ).

Детектор речи: **Silero VAD v5 в ONNX** (2.3 МБ, MIT, окно 32 мс; onnxruntime уже есть) против
WebRTC VAD (хуже в шуме) и пакета `silero-vad` (тянет torch).

## Решение
- Необязательная группа `stt`: `faster-whisper`, `numpy`, `onnxruntime` (`uv sync --all-extras`).
- Модели — вне git: `models/stt/whisper-turbo/` из `deepdml/faster-whisper-large-v3-turbo-ct2`
  (ревизия `4df90f7`: `model.bin`, `config.json`, `preprocessor_config.json`, `tokenizer.json`,
  `vocabulary.json`); `models/stt/vad/silero_vad.onnx` из `snakers4/silero-vad` тега `v5.1.2`.
- Порты раздельны: `VadPort` (каждое окно, CPU), `STTPort` (готовый отрезок). Whisper не потоковый:
  промежуточная гипотеза — тот же вызов на накопленном звуке с жадным поиском.
- `[stt.whisper].device = "auto"`: на GPU — видеокарта, иначе CPU. Точность: `int8` на CPU,
  `int8_float16` на GPU.

## Последствия
- Лицензии — MIT (модели и пакеты, `docs/licenses.md`).
- На CTranslate2 с GPU нужны библиотеки CUDA 12 (cuBLAS): на целевой машине проверить. Нет их —
  `device = "cpu"`, но turbo на CPU медленна: для CPU взять `small`.
- Whisper на видеокарте конкурирует с LLM за VRAM и время: совместная работа и бюджет 1.5 с
  проверяются при следующей аренде.
