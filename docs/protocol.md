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

### `setup.install` — `SetupInstall`

UI → Ядро: согласие на загрузку; без этого сообщения ничего не скачивается (S-13.2).

| Поле `data` | Тип |
|---|---|
| `item_ids` | `string[]` |
| `voice` | `string` |

### `setup.cancel` — `SetupCancel`

UI → Ядро: прервать загрузку; скачанное продолжится при следующей попытке.

`data`: `{}`

### `privacy.set` — `PrivacySet`

UI → Ядро: разговор не запоминается (S-17.2).

| Поле `data` | Тип |
|---|---|
| `enabled` | `boolean` |

### `memory.erase` — `MemoryErase`

UI → Ядро: удалить всю память.

| Поле `data` | Тип |
|---|---|
| `confirm` | `boolean` |

### `memory.list` — `MemoryList`

UI → Ядро: открыта панель памяти, нужен список.

`data`: `{}`

### `memory.transfer` — `MemoryTransfer`

UI → Ядро: перенести факты о пользователе в другое издание (S-20.10).

`data`: `{}`

### `memory.fact_save` — `MemoryFactSave`

UI → Ядро: исправить факт.

| Поле `data` | Тип |
|---|---|
| `note` | `string` |
| `text` | `string` |

### `memory.fact_delete` — `MemoryFactDelete`

UI → Ядро: удалить факт.

| Поле `data` | Тип |
|---|---|
| `note` | `string` |

### `branch.go` — `BranchGo`

UI → Ядро: вернуться к реплике; следующая реплика начнёт новую ветку.

| Поле `data` | Тип |
|---|---|
| `turn` | `string` |

### `branch.checkpoint` — `BranchCheckpoint`

UI → Ядро: запомнить текущее место под именем.

| Поле `data` | Тип |
|---|---|
| `name` | `string` |

### `window.visibility` — `WindowVisibility`

UI → Ядро: окно свернули или вернули; свёрнутому персонаж сам не заговорит (S-15.1).

| Поле `data` | Тип |
|---|---|
| `visible` | `boolean` |

### `chats.action` — `ChatAction`

UI → Ядро: действие со списком чатов.

| Поле `data` | Тип |
|---|---|
| `action` | `ChatVerb` |
| `id` | `string | null` |
| `name` | `string | null` |
| `category` | `string | null` |

### `chat.send_image` — `ChatSendImage`

UI → Ядро: новая реплика с картинкой; прерывает текущий ход, как `chat.send`.

| Поле `data` | Тип |
|---|---|
| `text` | `string` |
| `image` | `ImageData` |

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

### `avatar.gesture` — `AvatarGesture`

Ядро → UI: жест по смыслу фразы; модель без такого жеста его пропускает (S-18.4).

| Поле `data` | Тип |
|---|---|
| `gesture` | `Gesture` |

### `chat.attachment` — `ChatAttachment`

Ядро → UI: показать текст отдельным сообщением; озвучки у него нет.

| Поле `data` | Тип |
|---|---|
| `title` | `string` |
| `text` | `string` |

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

### `setup.state` — `SetupStateMessage`

Ядро → UI: нужен ли мастер и что он предлагает; приходит при подключении.

| Поле `data` | Тип |
|---|---|
| `needed` | `boolean` |
| `gpu_total_mb` | `number | null` |
| `voices` | `string[]` |
| `voice` | `string` |
| `warnings` | `string[]` |
| `items` | `SetupItemData[]` |

### `setup.progress` — `SetupProgress`

Ядро → UI: ход загрузки.

| Поле `data` | Тип |
|---|---|
| `done` | `number` |
| `total` | `number` |
| `file` | `string` |

### `setup.finished` — `SetupFinished`

Ядро → UI: установка закончена; после успеха приложение перезапускается.

| Поле `data` | Тип |
|---|---|
| `problem` | `string | null` |

### `viewer.blocked` — `ViewerBlockedMessage`

Ядро → UI: реплика зрителя заблокирована как атака; ведущий решает, что делать (FR-31).

| Поле `data` | Тип |
|---|---|
| `author` | `string` |
| `text` | `string` |

### `backend.notice` — `BackendNoticeMessage`

Ядро → UI: компонент упал, поднимается или снова работает (S-17.1).

| Поле `data` | Тип |
|---|---|
| `text` | `string` |

### `privacy.state` — `PrivacyState`

Ядро → UI: состояние режима; приходит при подключении и после переключения.

| Поле `data` | Тип |
|---|---|
| `enabled` | `boolean` |
| `erasable` | `boolean` |

### `memory.erased` — `MemoryErased`

Ядро → UI: итог очистки.

| Поле `data` | Тип |
|---|---|
| `problem` | `string | null` |

### `memory.transferred` — `MemoryTransferred`

Ядро → UI: перенос закончен (идёт в простое, поэтому — отдельным сообщением).

| Поле `data` | Тип |
|---|---|
| `count` | `number | null` |
| `problem` | `string | null` |

### `memory.facts` — `MemoryFacts`

Ядро → UI: факты памяти (S-16.2).

| Поле `data` | Тип |
|---|---|
| `facts` | `FactData[]` |
| `problem` | `string | null` |

### `branch.state` — `BranchState`

Ядро → UI: состояние диалога после перехода или при подключении.

| Поле `data` | Тип |
|---|---|
| `messages` | `BranchMessageData[]` |
| `branches` | `BranchData[]` |
| `checkpoints` | `CheckpointData[]` |
| `problem` | `string | null` |

### `chat.sources` — `ChatSources`

Ядро → UI: инструмент нашёл источники для этого ответа (FR-25).

| Поле `data` | Тип |
|---|---|
| `sources` | `SourceData[]` |

### `app.edition` — `AppEdition`

Ядро → UI при подключении: в каком издании запущено ядро; UI сверяет с выбором на экране.

| Поле `data` | Тип |
|---|---|
| `id` | `string` |
| `language` | `string` |
| `content_profile` | `string` |
| `stream_safe` | `boolean` |

### `chats.state` — `ChatsState`

Ядро → UI: список чатов после любого изменения и при подключении.

| Поле `data` | Тип |
|---|---|
| `chats` | `ChatItemData[]` |
| `categories` | `CategoryData[]` |
| `active` | `string` |
| `switching` | `boolean` |
| `problem` | `string | null` |

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
