/**
 * Состояние приложения на рунах Svelte: связь с ядром, бэкенды, ход, история чата, метрики.
 * Меняется только методами — их зовут транспорт (сообщения ядра) и действия пользователя.
 * Дельты пока применяются по одной; батчинг по кадрам (T-16, R-65) — в S-5.3.
 */
import type {
  BackendState,
  Component,
  Emotion,
  ErrorData,
  OutboundMessage,
  TurnCancelledMessage,
} from "./protocol.gen";
import type { ConnectionState } from "./transport";

export type Role = "user" | "assistant";
export type MessageStatus = "streaming" | "done" | "cancelled";
/** Фаза хода для аватара и кнопки «Стоп»: ждём первый токен / идёт ответ / ничего. */
export type TurnPhase = "idle" | "thinking" | "speaking";

export interface ChatMessage {
  id: number;
  role: Role;
  text: string;
  /** Ход ядра; у реплик пользователя — null. */
  turn: string | null;
  status: MessageStatus;
}

/** Сколько последних замеров стадии хранить: хватает на p95, память — копейки. */
export const SPAN_HISTORY = 100;

/** Что звучит в плеере (сообщает фича звука): ход, идёт ли звук, сыграно и получено, секунд. */
export interface SpeechProgress {
  turn: string;
  speaking: boolean;
  playedS: number;
  receivedS: number;
}

/**
 * Голос в UI. Ход ядра заканчивается, когда синтез готов, а звучит голос дольше (синтез
 * быстрее речи), — поэтому «говорит» знает только плеер, а не фаза хода.
 */
export interface VoiceState {
  /** Последнее, что звучало; null — ещё ничего. */
  speech: SpeechProgress | null;
}

export class AppStore {
  connection = $state<ConnectionState>("closed");
  backends = $state<Record<Component, BackendState | "unknown">>({
    llm: "unknown",
    tts: "unknown",
    stt: "unknown",
  });
  messages = $state<ChatMessage[]>([]);
  phase = $state<TurnPhase>("idle");
  turn = $state<string | null>(null);
  emotion = $state<Emotion>("neutral");
  error = $state<ErrorData | null>(null);
  /** Последние замеры каждой стадии, мс, от старых к новым (панель метрик, FR-15). */
  spans = $state<Record<string, number[]>>({});
  voice = $state<VoiceState>({ speech: null });
  /** Промежуточный текст фразы, которую сейчас говорит пользователь (Этап 11). */
  hypothesis = $state("");

  #nextId = 0;
  /** Индекс сообщения текущего хода в `messages`: массив только растёт, индекс не сдвигается. */
  #streaming: number | null = null;

  addUserMessage(text: string): void {
    this.#push("user", text, null, "done");
    this.error = null;
  }

  /** Замер стадии: от ядра (`metrics.span`) или измеренный самим UI (`ui.*`). */
  recordSpan(name: string, ms: number): void {
    const history = this.spans[name];
    if (history === undefined) {
      this.spans[name] = [ms];
      return;
    }
    history.push(ms);
    if (history.length > SPAN_HISTORY) {
      history.shift();
    }
  }

  /** Плеер: звук идёт, кончился или продвинулся. */
  setSpeech(progress: SpeechProgress): void {
    this.voice.speech = progress;
  }

  /** Разрыв посреди хода: ядро отменяет ход само (T-14), а `turn.cancelled` уже не дойдёт. */
  setConnection(state: ConnectionState): void {
    this.connection = state;
    if (state !== "open" && state !== "connecting") {
      this.#endTurn("cancelled");
    }
  }

  apply(message: OutboundMessage): void {
    switch (message.type) {
      case "turn.started":
        this.#startTurn(message.turn);
        break;
      case "chat.delta":
        this.#appendDelta(message.turn, message.data.text);
        break;
      case "avatar.emotion":
        if (message.turn === this.turn) this.emotion = message.data.emotion;
        break;
      case "turn.finished":
        if (message.turn === this.turn) this.#endTurn("done");
        break;
      case "turn.cancelled":
        this.#cancelTurn(message);
        break;
      case "metrics.span":
        this.recordSpan(message.data.name, message.data.ms);
        break;
      case "status":
        this.backends[message.data.component] = message.data.state;
        break;
      case "error":
        this.error = message.data;
        break;
      case "input.hypothesis":
        this.hypothesis = message.data.text;
        break;
      case "input.final":
        this.hypothesis = "";
        this.addUserMessage(message.data.text);
        break;
      case "input.barge_in":
        // Голос глушит клиент сразу, мимо пачки; состояние хода изменит `turn.cancelled`.
        break;
      default:
        message satisfies never;
    }
  }

  #push(role: Role, text: string, turn: string | null, status: MessageStatus): number {
    this.#nextId += 1;
    return this.messages.push({ id: this.#nextId, role, text, turn, status }) - 1;
  }

  #startTurn(turn: string): void {
    this.#endTurn("cancelled");
    this.turn = turn;
    this.phase = "thinking";
    this.emotion = "neutral";
    this.#streaming = this.#push("assistant", "", turn, "streaming");
  }

  /** Дельта чужого хода — хвост отменённого ответа, уже летевший по сокету: отбрасывается. */
  #appendDelta(turn: string, text: string): void {
    const message = this.#current();
    if (message?.turn !== turn) {
      return;
    }
    message.text += text;
    this.phase = "speaking";
  }

  #cancelTurn(message: TurnCancelledMessage): void {
    if (message.turn !== this.turn) {
      return;
    }
    this.#endTurn("cancelled");
  }

  #endTurn(status: MessageStatus): void {
    const message = this.#current();
    if (message !== undefined) {
      message.status = status;
    }
    this.#streaming = null;
    this.turn = null;
    this.phase = "idle";
  }

  #current(): ChatMessage | undefined {
    return this.#streaming === null ? undefined : this.messages[this.#streaming];
  }
}
