/**
 * Точка входа фич в ядро: store для чтения состояния и действия пользователя. Фичи не держат
 * транспорт сами (R-63) — так связь, очередь и переподключение живут в одном месте.
 */
import type { AudioFrame } from "./frames";
import { PROTOCOL_VERSION } from "./protocol.gen";
import { AppStore } from "./store.svelte";
import { Transport, type Backoff, type SocketFactory } from "./transport";

/** 250 мс → ×2 → потолок 5 с: ядро на localhost поднимается за секунды, чаще стучаться незачем. */
const BACKOFF: Backoff = { initialMs: 250, maxMs: 5000, factor: 2 };
/** Реплики, набранные за время разрыва; больше — уже не диалог, а пачка устаревших сообщений. */
const QUEUE_LIMIT = 16;

export type AudioSink = (frame: AudioFrame) => void;

export interface CoreClientOptions {
  url: string;
  socketFactory?: SocketFactory;
}

export class CoreClient {
  readonly store = new AppStore();
  readonly #transport: Transport;
  /** Аудиоплеер подключается на Этапе 8; до него кадры отбрасываются. */
  #audio: AudioSink = () => undefined;

  constructor(options: CoreClientOptions) {
    const store = this.store;
    this.#transport = new Transport(
      { ...options, backoff: BACKOFF, queueLimit: QUEUE_LIMIT },
      {
        message: (message) => {
          store.apply(message);
        },
        audio: (frame) => {
          this.#audio(frame);
        },
        connection: (state) => {
          store.setConnection(state);
        },
        protocolError: (reason) => {
          console.warn(`[transport] ${reason}`);
        },
      },
    );
  }

  start(): void {
    this.#transport.start();
  }

  dispose(): void {
    this.#transport.stop();
  }

  onAudio(sink: AudioSink): void {
    this.#audio = sink;
  }

  /** Реплика пользователя: в историю сразу (T-17), ядру — новым ходом. */
  say(text: string): void {
    const trimmed = text.trim();
    if (trimmed === "") {
      return;
    }
    this.store.addUserMessage(trimmed);
    this.#transport.send({ v: PROTOCOL_VERSION, type: "chat.send", data: { text: trimmed } });
  }

  stop(): void {
    this.#transport.send({ v: PROTOCOL_VERSION, type: "chat.cancel", data: {} });
  }
}
