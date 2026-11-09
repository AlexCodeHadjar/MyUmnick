# domain — неизменяемые сущности и значения диалога, речи и эмоций

## Ответственность
Словарь ядра: роли, сообщения, ходы, персона, эмоции и формат их тегов, формат звука, события
шины, доменные ошибки. Только данные и чистые функции. НЕ делает ввода-вывода, не валидирует
внешние данные (это границы: kernel/config, gateway, адаптеры), не знает о pydantic, httpx,
websockets, torch и о kernel (контракт `domain-pure`). Ошибка — только сообщение «что делать»
(R-45), без кодов.

## Публичный API (`__init__.py`)
| Символ | Назначение |
|---|---|
| `viewer_line`, `is_viewer_line`, `looks_like_attack`, `VIEWER_PREFIX`, `ViewerBlocked` | Реплика зрителя как данные и признаки явных атак (FR-31); правила обходятся, граница — отсутствие инструментов и памяти у зрителя |
| `EditionId`, `ContentProfile` | Издание (`ru`, `en`) и профиль содержания (`standard`, `unfiltered`) — Этап 20, ADR-0032 |
| `GpuMemory(total_mb, used_mb)` | Видеопамять: всего и занято всеми программами (ADR-0018) |
| `PhraseVoiced(text, starts_in_s, duration_s)` | Событие: фраза озвучена; время — оценка по отданному звуку |
| `IncomingMessage(source, author, text)` | Реплика извне: сообщение зрителя |
| `Role`, `Message` | Роль (`system`/`user`/`assistant`) и сообщение контекста LLM |
| `TurnId`, `Turn` | Номер хода (uint64 в аудиокадре) и завершённый ход; `is_interrupted` — ответ прерван |
| `Persona` | Характер витюбера из `personas/*.toml`; в `rules` возможен `{emotions}` |
| `Emotion` | Единственный список эмоций; `.tag` → `<happy>` |
| `parse_tag`, `TAG_OPEN`, `TAG_CLOSE`, `MAX_TAG_LENGTH` | Разбор тега эмоции; предел буфера для StreamParser |
| `AudioFormat`, `AudioChunk`, `SAMPLE_WIDTH_BYTES` | PCM s16le моно; `duration_s` для RTF и пауз |
| `Fact`, `FactSource`, `FactHit`, `FactId` | Долговременная память (FR-10): текст, источник (`user`/`extracted`/`summary`), важность 0…1, время с поясом; найденный факт с близостью |
| `Vector`, `EmbedKind` | Эмбеддинг (`tuple[float, ...]`, единичной длины); запрос или запоминаемый текст (e5) |
| `TurnStarted`, `TurnFinished`, `TurnCancelled`, `EmotionChanged`, `BackendStatusChanged` | События шины |
| `MetricRecorded` | Замер стадии: `name`, `duration_ns`, `turn_id` (None вне хода) |
| `TurnState`, `next_state` | Состояния хода и разрешённые переходы; иначе `TurnStateError` |
| `CancelReason`, `Component`, `BackendState` | Значения событий |
| `VtuberError` → `BackendUnavailable` (`LLMUnavailable`, `TTSUnavailable`, `MemoryUnavailable`), `GenerationFailed`, `ProtocolError`, `ConfigError`, `TurnStateError` | Доменные ошибки |

## Зависимости
- Только stdlib.

## События
- Определяет события шины; сам ничего не публикует и не слушает.

## Инварианты
- Все dataclass — `frozen=True, slots=True` (проверяет `tests/unit/domain/test_package.py`).
- Каждый публичный класс и функция модулей пакета перечислены в `__all__` (тот же тест).
- `parse_tag(emotion.tag) is emotion` для каждой эмоции; регистр и пробелы в скобках не важны.
- Значения `Emotion` — строчные латинские слова: они же имена тегов и ключи `mapping.json`.
- Значения Enum-ов — строки протокола UI; их смена — изменение протокола.

## Производительность
- Горячий путь: `parse_tag` и `MAX_TAG_LENGTH` использует StreamParser; `AudioChunk` идёт по
  очереди TTS → sink. Без копирования PCM (R-41).

## Как расширять
- Новая эмоция — значение в `Emotion` + выражение в `avatar/<model>/mapping.json`.
- Новый бэкенд в статус-баре — значение в `Component` (STT — Этап 11, память — Этап 10).
- Причина отмены barge-in — `CancelReason` (Этап 11).
- Новая ошибка — подкласс `VtuberError`; адаптер переводит в неё чужие исключения.

## Кто использует
- Все слои, включая kernel (ADR-0005): `ConfigError` бросает `kernel.load_config`, `TurnId`
  привязывает `kernel.turn_context`, `MetricRecorded` публикует `kernel.Telemetry`.

## Связанные документы
`docs/architecture.md` (Слои, StreamParser, Ошибки, Протокол), ADR-0001, ADR-0003, T-15, T-17
