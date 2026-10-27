/**
 * Точка входа фич в ядро: store для чтения состояния и действия пользователя. Фичи не держат
 * транспорт сами (R-63) — так связь, очередь и переподключение живут в одном месте.
 */
import { animationFrame, FrameBatch, type FrameScheduler } from "./batch";
import type { AudioFrame } from "./frames";
import { FIRST_CHAR_SPAN, FirstCharProbe } from "./probe";
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
  /** Когда применять входящие к store; по умолчанию — раз в кадр (T-16). */
  scheduleFrame?: FrameScheduler;
  /** Часы для замеров UI, мс; по умолчанию — `performance.now`. */
  now?: () => number;
}

export class CoreClient {
  readonly store = new AppStore();
  readonly #transport: Transport;
  /** Аудиоплеер подключается на Этапе 8; до него кадры отбрасываются. */
  #audio: AudioSink = () => undefined;
  readonly #probe: FirstCharProbe;

  constructor(options: CoreClientOptions) {
    const { url, socketFactory, scheduleFrame = animationFrame } = options;
    const store = this.store;
    const batch = new FrameBatch(scheduleFrame);
    const probe = new FirstCharProbe(options.now ?? (() => performance.now()));
    this.#probe = probe;
    this.#transport = new Transport(
      {
        url,
        backoff: BACKOFF,
        queueLimit: QUEUE_LIMIT,
        ...(socketFactory === undefined ? {} : { socketFactory }),
      },
      {
        message: (message) => {
          batch.run(() => {
            store.apply(message);
            const ms = probe.observe(message);
            if (ms !== null) store.recordSpan(FIRST_CHAR_SPAN, ms);
          });
        },
        // Звук — мимо пачки: плееру важна каждая миллисекунда (TTFA), DOM он не трогает.
        audio: (frame) => {
          this.#audio(frame);
        },
        connection: (state) => {
          batch.run(() => {
            store.setConnection(state);
          });
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
    this.#probe.sent();
    this.#transport.send({ v: PROTOCOL_VERSION, type: "chat.send", data: { text: trimmed } });
  }

  stop(): void {
    this.#transport.send({ v: PROTOCOL_VERSION, type: "chat.cancel", data: {} });
  }
}
