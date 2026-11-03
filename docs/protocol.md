# Протокол UI ↔ Ядро

> Автогенерация: `uv run python tools/gen_protocol.py`. Не редактировать.
> Источник — `src/vtuber/gateway/protocol.py`; TS-типы — `ui/src/core/protocol.gen.ts`.

Версия протокола: **1**. Текстовый кадр WebSocket — JSON-конверт
`{"v": 1, "type": "…", "turn": "t-000042", "data": {…}}`; `turn` есть у сообщений хода.
Все поля обязательны; отсутствие значения — явный `null`.

## UI → Ядро

### `chat.send` — `ChatSend`

UI → Ядро: новая реплика; прерывает текущий ход.

| Поле `data` | Тип |
|---|---|
| `text` | `string` |

### `chat.cancel` — `ChatCancel`

UI → Ядро: остановить ответ.

`data`: `{}`

### `input.typing` — `InputTyping`

UI → Ядро: черновик реплики (с дебаунсом ~300 мс) — прогрев кэша LLM, T-05.

| Поле `data` | Тип |
|---|---|
| `text` | `string` |

### `resources.watch` — `ResourcesWatch`

UI → Ядро: панель ресурсов открыли или закрыли; закрытая ничего не считает.

| Поле `data` | Тип |
|---|---|
| `enabled` | `boolean` |

## Ядро → UI

### `turn.started` — `TurnStartedMessage`

Ядро → UI: ход начат — аватар «думает» (T-17).

`data`: `{}`

### `chat.delta` — `ChatDelta`

Ядро → UI: порция текста ответа.

| Поле `data` | Тип |
|---|---|
| `text` | `string` |

### `avatar.emotion` — `AvatarEmotion`

Ядро → UI: сменить выражение аватара.

| Поле `data` | Тип |
|---|---|
| `emotion` | `Emotion` |
| `intensity` | `number` |

### `turn.finished` — `TurnFinishedMessage`

Ядро → UI: ответ закончен полностью.

`data`: `{}`

### `turn.cancelled` — `TurnCancelledMessage`

Ядро → UI: ход прерван — UI сбрасывает аудиобуфер.

| Поле `data` | Тип |
|---|---|
| `reason` | `CancelReason` |
| `message` | `string` |

### `metrics.span` — `MetricsSpan`

Ядро → UI: замер стадии; `turn` — None вне хода (прогрев).

| Поле `data` | Тип |
|---|---|
| `name` | `string` |
| `ms` | `number` |

### `status` — `Status`

Ядро → UI: состояние бэкенда (вне хода).

| Поле `data` | Тип |
|---|---|
| `component` | `Component` |
| `state` | `BackendState` |

### `input.barge_in` — `InputBargeIn`

Ядро → UI: пользователь заговорил — оборвать голос витюбера сразу (Этап 11).

`data`: `{}`

### `input.hypothesis` — `InputHypothesis`

Ядро → UI: промежуточный текст фразы пользователя.

| Поле `data` | Тип |
|---|---|
| `text` | `string` |

### `input.final` — `InputFinal`

Ядро → UI: распознанная фраза — реплика пользователя в чате; за ней начнётся ход.

| Поле `data` | Тип |
|---|---|
| `text` | `string` |

### `resources.snapshot` — `ResourcesMessage`

Ядро → UI: снимок для панели ресурсов, только пока она открыта (S-12.10).

| Поле `data` | Тип |
|---|---|
| `limit_mb` | `number` |
| `capacity_mb` | `number` |
| `free_mb` | `number` |
| `pinned` | `PinnedModelData[]` |
| `models` | `ManagedModelData[]` |

### `error` — `ErrorMessage`

Ядро → UI: ошибка; `turn` — None, если не относится к ходу (битое сообщение).

| Поле `data` | Тип |
|---|---|
| `code` | `ErrorCode` |
| `message` | `string` |

## Бинарный аудиокадр (Ядро → UI)

| Смещение | Размер | Поле |
|---|---|---|
| 0 | 1 | тип кадра (`0x01` = audio) |
| 1 | 1 | версия протокола |
| 2 | 2 | `seq` (uint16, LE, по модулю 2^16) |
| 4 | 4 | `sample_rate` (uint32, LE) |
| 8 | 8 | `turn_id` (uint64, LE) |
| 16 | … | PCM s16le, моно |
