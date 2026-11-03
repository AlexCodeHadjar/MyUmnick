// Автогенерация: `uv run python tools/gen_protocol.py`. Не редактировать.

export const PROTOCOL_VERSION = 1 as const;

/** Ядро → UI: сменить выражение аватара. */
export interface AvatarEmotion {
  v: Version;
  type: "avatar.emotion";
  turn: string;
  data: EmotionData;
}

/** Состояние бэкенда для статус-бара UI. */
export type BackendState = "loading" | "ready" | "failed";

/** Почему ход прерван. */
export type CancelReason = "user_stop" | "new_message" | "barge_in" | "error";

/** Почему ход прерван; `message` — текст ошибки при `reason == "error"`. */
export interface CancelledData {
  reason: CancelReason;
  message: string;
}

/** UI → Ядро: остановить ответ. */
export interface ChatCancel {
  v: Version;
  type: "chat.cancel";
  data: EmptyData;
}

/** Ядро → UI: порция текста ответа. */
export interface ChatDelta {
  v: Version;
  type: "chat.delta";
  turn: string;
  data: DeltaData;
}

/** UI → Ядро: новая реплика; прерывает текущий ход. */
export interface ChatSend {
  v: Version;
  type: "chat.send";
  data: SendData;
}

/** Бэкенд, о состоянии которого сообщается в UI. */
export type Component = "llm" | "tts" | "stt";

/** Порция текста ответа. */
export interface DeltaData {
  text: string;
}

/** Единственный источник списка эмоций: из него строятся промпт персоны и разбор ответа. */
export type Emotion = "neutral" | "happy" | "sad" | "angry" | "surprised" | "embarrassed" | "thinking";

/** Эмоция аватара; `intensity` 0…1 (затухание — Этап 8). */
export interface EmotionData {
  emotion: Emotion;
  intensity: number;
}

/** Сообщение без полезной нагрузки. */
export type EmptyData = Record<string, never>;

/** Что пошло не так — UI выбирает реакцию по коду, текст показывает пользователю. */
export type ErrorCode = "bad_message" | "llm_unavailable" | "generation_failed" | "internal";

/** Ошибка для пользователя. */
export interface ErrorData {
  code: ErrorCode;
  message: string;
}

/** Ядро → UI: ошибка; `turn` — None, если не относится к ходу (битое сообщение). */
export interface ErrorMessage {
  v: Version;
  type: "error";
  turn: string | null;
  data: ErrorData;
}

/** Итог установки: `problem` — None, если всё поставлено. */
export interface FinishedData {
  problem: string | null;
}

/** Ядро → UI: пользователь заговорил — оборвать голос витюбера сразу (Этап 11). */
export interface InputBargeIn {
  v: Version;
  type: "input.barge_in";
  data: EmptyData;
}

/** Ядро → UI: распознанная фраза — реплика пользователя в чате; за ней начнётся ход. */
export interface InputFinal {
  v: Version;
  type: "input.final";
  data: DeltaData;
}

/** Ядро → UI: промежуточный текст фразы пользователя. */
export interface InputHypothesis {
  v: Version;
  type: "input.hypothesis";
  data: DeltaData;
}

/** UI → Ядро: черновик реплики (с дебаунсом ~300 мс) — прогрев кэша LLM, T-05. */
export interface InputTyping {
  v: Version;
  type: "input.typing";
  data: TypingData;
}

/** Что выбрал пользователь в мастере. */
export interface InstallData {
  item_ids: string[];
  voice: string;
}

/** Модель под управлением менеджера; `waiting_reason` — почему ждёт. */
export interface ManagedModelData {
  name: string;
  vram_mb: number;
  priority: string;
  state: string;
  users: number;
  waiting_reason: string | null;
}

/** Ядро → UI: замер стадии; `turn` — None вне хода (прогрев). */
export interface MetricsSpan {
  v: Version;
  type: "metrics.span";
  turn: string | null;
  data: SpanData;
}

/** Закреплённая модель: основная LLM, распознавание речи. */
export interface PinnedModelData {
  name: string;
  vram_mb: number;
}

/** Сколько байт готово из общего числа и какой файл качается. */
export interface ProgressData {
  done: number;
  total: number;
  file: string;
}

/** Снимок видеопамяти: `limit_mb` учитывает другие программы, `capacity_mb` — только конфиг. */
export interface ResourcesData {
  limit_mb: number;
  capacity_mb: number;
  free_mb: number;
  pinned: PinnedModelData[];
  models: ManagedModelData[];
}

/** Ядро → UI: снимок для панели ресурсов, только пока она открыта (S-12.10). */
export interface ResourcesMessage {
  v: Version;
  type: "resources.snapshot";
  data: ResourcesData;
}

/** UI → Ядро: панель ресурсов открыли или закрыли; закрытая ничего не считает. */
export interface ResourcesWatch {
  v: Version;
  type: "resources.watch";
  data: WatchData;
}

/** Реплика пользователя. */
export interface SendData {
  text: string;
}

/** UI → Ядро: прервать загрузку; скачанное продолжится при следующей попытке. */
export interface SetupCancel {
  v: Version;
  type: "setup.cancel";
  data: EmptyData;
}

/** Состояние мастера: `gpu_total_mb` — None, если карта NVIDIA не найдена. */
export interface SetupData {
  needed: boolean;
  gpu_total_mb: number | null;
  voices: string[];
  voice: string;
  warnings: string[];
  items: SetupItemData[];
}

/** Ядро → UI: установка закончена; после успеха приложение перезапускается. */
export interface SetupFinished {
  v: Version;
  type: "setup.finished";
  data: FinishedData;
}

/** UI → Ядро: согласие на загрузку; без этого сообщения ничего не скачивается (S-13.2). */
export interface SetupInstall {
  v: Version;
  type: "setup.install";
  data: InstallData;
}

/** Компонент в мастере; `license` пользователь видит до согласия. */
export interface SetupItemData {
  id: string;
  title: string;
  license: string;
  size: number;
  required: boolean;
  recommended: boolean;
  installed: boolean;
}

/** Ядро → UI: ход загрузки. */
export interface SetupProgress {
  v: Version;
  type: "setup.progress";
  data: ProgressData;
}

/** Ядро → UI: нужен ли мастер и что он предлагает; приходит при подключении. */
export interface SetupStateMessage {
  v: Version;
  type: "setup.state";
  data: SetupData;
}

/** Замер стадии хода для панели метрик (FR-15). */
export interface SpanData {
  name: string;
  ms: number;
}

/** Ядро → UI: состояние бэкенда (вне хода). */
export interface Status {
  v: Version;
  type: "status";
  data: StatusData;
}

/** Состояние бэкенда для статус-бара. */
export interface StatusData {
  component: Component;
  state: BackendState;
}

/** Ядро → UI: ход прерван — UI сбрасывает аудиобуфер. */
export interface TurnCancelledMessage {
  v: Version;
  type: "turn.cancelled";
  turn: string;
  data: CancelledData;
}

/** Ядро → UI: ответ закончен полностью. */
export interface TurnFinishedMessage {
  v: Version;
  type: "turn.finished";
  turn: string;
  data: EmptyData;
}

/** Ядро → UI: ход начат — аватар «думает» (T-17). */
export interface TurnStartedMessage {
  v: Version;
  type: "turn.started";
  turn: string;
  data: EmptyData;
}

/** Черновик реплики, пока пользователь печатает; пустой — поле очищено. */
export interface TypingData {
  text: string;
}

export type Version = 1;

/** Открыта ли панель ресурсов. */
export interface WatchData {
  enabled: boolean;
}

export type InboundMessage = ChatSend | ChatCancel | InputTyping | ResourcesWatch | SetupInstall | SetupCancel;

export type OutboundMessage = TurnStartedMessage | ChatDelta | AvatarEmotion | TurnFinishedMessage | TurnCancelledMessage | MetricsSpan | Status | InputBargeIn | InputHypothesis | InputFinal | ResourcesMessage | SetupStateMessage | SetupProgress | SetupFinished | ErrorMessage;
