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
export type CancelReason = "user_stop" | "new_message" | "error";

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
export type Component = "llm" | "tts";

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

/** UI → Ядро: черновик реплики (с дебаунсом ~300 мс) — прогрев кэша LLM, T-05. */
export interface InputTyping {
  v: Version;
  type: "input.typing";
  data: TypingData;
}

/** Ядро → UI: замер стадии; `turn` — None вне хода (прогрев). */
export interface MetricsSpan {
  v: Version;
  type: "metrics.span";
  turn: string | null;
  data: SpanData;
}

/** Реплика пользователя. */
export interface SendData {
  text: string;
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

export type InboundMessage = ChatSend | ChatCancel | InputTyping;

export type OutboundMessage = TurnStartedMessage | ChatDelta | AvatarEmotion | TurnFinishedMessage | TurnCancelledMessage | MetricsSpan | Status | ErrorMessage;
