# Этап 7 — Голос: TTS, конвейер, воспроизведение, липсинк

## Цель
Витюбер говорит, звук начинается до окончания генерации, рот синхронен. Ключевой этап для TTFA.

## Зависимости
Этапы 3, 4, 6.

## Критерии приёмки этапа
- [ ] TTFA p50 ≤ 800 мс (RTX 5070 Ti).
- [ ] RTF выбранного TTS ≤ 0.3; паузы между фразами ≤ 80 мс сверх естественных.
- [ ] Отмена → тишина ≤ 100 мс.
- [ ] Рот не двигается в паузах и не «запаздывает» визуально.

## Подводные камни
- **Лицензии голосов** (`docs/licenses.md`): Silero TTS — CC BY-NC 4.0 (некоммерческая);
  Piper ru: `denis`, `dmitri` — CC0, `ruslan` — CC BY-NC-SA, `irina` — неизвестна; новый движок
  Piper (piper1-gpl) — GPL. Выбор голоса учитывает лицензию.
- Разная частота дискретизации у движков: формат — в `TTSPort.audio_format`, ресемплинг — в UI.
- Первая фраза из 1–2 слов звучит неестественно — поэтому `first_min_words = 4`.

## Сессии

### S-7.1 — Порт TTS, фейк, контрактный тест
- **Цель:** `TTSPort`, `FakeTTS(rtf)`, `tests/contract/test_tts_contract.py`.
- **Scope:** `src/vtuber/ports/tts.py`, `tests/fakes/`, `tests/contract/`
- **Читать:** `docs/testing.md` (Контрактные тесты)
- **Готово, когда:** [x] контракт (формат, отмена) проходит для FakeTTS.
- **Статус:** готово

### S-7.2 — SentenceChunker и нормализатор
- **Цель:** `SentenceChunker` (T-02) с property-based тестами; `application/speech/normalizer.py`
  (числа словами с базовым падежом, сокращения, латиница, без эмодзи/markdown).
- **Scope:** `application/pipeline/chunker.py`, `application/speech/`
- **Читать:** `docs/architecture.md` (SentenceChunker), `docs/performance.md` (T-02)
- **Готово, когда:**
  - [ ] Тест `test_first_phrase_is_cut_after_four_words_at_comma`; `3.5` и `т.е.` не режутся.
- **Статус:** не начата

### S-7.3 — Адаптер Silero
- **Цель:** `SileroTTS`: модель грузится один раз (R-40), синтез в `asyncio.to_thread`,
  ограничение потоков CPU, PCM s16le.
- **Scope:** `adapters/tts/silero.py`, карточка `adapters/tts/README.md`
- **Готово, когда:** [ ] контрактный тест проходит; RTF замерен.
- **Статус:** не начата

### S-7.4 — Адаптер Piper
- **Цель:** `PiperTTS` с тем же контрактом.
- **Scope:** `adapters/tts/piper.py`, `config/default.toml` (секция tts.piper)
- **Готово, когда:** [ ] контрактный тест проходит; RTF < 0.3 на `bench/prompts_ru.jsonl`.
- **Статус:** не начата

### S-7.5 — TTS-ветка конвейера, бинарные кадры
- **Цель:** TTS-ветка в ReplyPipeline (фраза N синтезируется параллельно с генерацией N+1);
  аудио уходит бинарными кадрами.
- **Scope:** `application/pipeline/reply_pipeline.py`, `gateway/sink.py`
- **Готово, когда:**
  - [ ] Тест: первая фраза ушла в TTS раньше, чем FakeLLM закончил.
- **Статус:** не начата

### S-7.6 — Аудиоплеер и липсинк в UI
- **Цель:** AudioWorklet-плеер с кольцевым буфером, короткий fade на стыках, сброс по
  `turn.cancelled`; AnalyserNode → RMS → сглаживание → `setMouth()`; `audio.played`.
- **Scope:** `ui/src/features/audio/`, `ui/src/features/avatar/`
- **Читать:** ADR-0003
- **Готово, когда:** [ ] ручной сценарий: без щелчков, рот синхронен, отмена ≤ 100 мс.
- **Статус:** не начата

### S-7.7 — Бенчмарк TTFA, ADR голоса
- **Цель:** TTFA, RTF, паузы между фразами в бенчмарке; ADR выбора голоса по таблице
  «качество 1–5 × RTF × TTFA × лицензия».
- **Scope:** `tools/bench_latency.py`, `docs/adr/`, `docs/licenses.md`
- **Готово, когда:** [ ] TTFA p50 ≤ 800 мс зафиксирован в ADR.
- **Статус:** не начата
