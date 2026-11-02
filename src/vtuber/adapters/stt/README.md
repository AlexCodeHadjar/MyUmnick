# adapters/stt — распознавание речи и детектор речи

## Ответственность
Реализации портов голосового ввода (ADR-0016): `WhisperSTT` — faster-whisper large-v3-turbo,
`SileroVad` — Silero VAD v5 в ONNX. НЕ решает, где кончилась фраза и когда распознавать
(`application/voice`), не ходит за моделями в сеть.

## Публичный API (`__init__.py`)
| Символ | Назначение |
|---|---|
| `WhisperSTT(cfg)` | `STTPort` в `async with`: `transcribe(audio, final=)`; нет модели — `STTUnavailable` на вызов |
| `WhisperConfig` | `[stt.whisper]`: `model_dir`, `language`, `device`, `compute_type`, `threads`, `final_beam` |
| `SileroVad(cfg)` | `VadPort` в `async with`: окно 512 сэмплов (32 мс, 16 кГц) → вероятность речи; `reset()` |
| `VadConfig` | `[stt.vad]`: `model_path`, `threads` |

## Зависимости
- Порты `STTPort`, `VadPort`; домен `AudioChunk`, `STTUnavailable`; группа `stt` (импорт ленивый).

## События
- Публикует: —
- Слушает: —

## Инварианты (`tests/contract/test_stt_contract.py`)
- VAD отличает речь от тишины; окно другой длины — `ValueError`; нет модели — `STTUnavailable`.
- STT распознаёт запись; пустой звук — пустая строка; нет модели — `STTUnavailable`.
- Работа с моделями — в потоке (R-34); Whisper под замком: отменённое распознавание дорабатывает.

## Производительность
- VAD — около миллисекунды на окно. Whisper turbo на этом ПК (CPU, int8) — медленнее речи; замер на
  GPU — при следующей аренде.

## Как расширять
- Другой движок: адаптер `STTPort` и случай в контрактном тесте.

## Связанные документы
ADR-0016, STAGE_11
