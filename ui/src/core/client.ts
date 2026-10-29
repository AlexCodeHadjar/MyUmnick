/**
 * Точка входа фич в ядро: store для чтения состояния и действия пользователя. Фичи не держат
 * транспорт сами (R-63) — так связь, очередь и переподключение живут в одном месте.
 */
import { animationFrame, FrameBatch, type FrameScheduler } from "./batch";
import type { AudioFrame } from "./frames";
import { FIRST_AUDIO_SPAN, FIRST_CHAR_SPAN, FirstAudioProbe, FirstCharProbe } from "./probe";
import { PROTOCOL_VERSION } from "./protocol.gen";
import { AppStore, type SpeechProgress } from "./store.svelte";
import { Transport, type Backoff, type SocketFactory } from "./transport";

/** 250 мс → ×2 → потолок 5 с: ядро на localhost поднимается за секунды, чаще стучаться незачем. */
const BACKOFF: Backoff = { initialMs: 250, maxMs: 5000, factor: 2 };
/** Реплики, набранные за время разрыва; больше — уже не диалог, а пачка устаревших сообщений. */
const QUEUE_LIMIT = 16;

export type AudioSink = (frame: AudioFrame) => void;
/** Звук хода надо оборвать: `turn` — отменённый ход, null — связь потеряна (сбросить всё). */
export type CancelSink = (turn: string | null) => void;

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
  /** Плеер подключается из фичи audio; до него кадры отбрасываются. */
  #audio: AudioSink = () => undefined;
  #cancel: CancelSink = () => undefined;
  readonly #batch: FrameBatch;
  readonly #probe: FirstCharProbe;
  readonly #audioProbe: FirstAudioProbe;

  constructor(options: CoreClientOptions) {
    const { url, socketFactory, scheduleFrame = animationFrame } = options;
    const store = this.store;
    const batch = new FrameBatch(scheduleFrame);
    this.#batch = batch;
    const now = options.now ?? (() => performance.now());
    const probe = new FirstCharProbe(now);
    const audioProbe = new FirstAudioProbe(now);
    this.#probe = probe;
    this.#audioProbe = audioProbe;
    this.#transport = new Transport(
      {
        url,
        backoff: BACKOFF,
        queueLimit: QUEUE_LIMIT,
        ...(socketFactory === undefined ? {} : { socketFactory }),
      },
      {
        message: (message) => {
          // Отмена — мимо пачки: тишина за ≤ 100 мс (NFR-04) не ждёт следующего кадра.
          if (message.type === "turn.cancelled") this.#cancel(message.turn);
          audioProbe.observe(message);
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
          // Разрыв отменяет ход на ядре (T-14), а `turn.cancelled` уже не придёт.
          if (state !== "open" && state !== "connecting") this.#cancel(null);
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

  onCancel(sink: CancelSink): void {
    this.#cancel = sink;
  }

  /** Плеер: что звучит. В store — пачкой раз в кадр, как и сообщения ядра (T-16). */
  speech(progress: SpeechProgress): void {
    this.#batch.run(() => {
      this.store.setSpeech(progress);
    });
  }

  /** Плеер: звук хода `turn` зазвучал — замер TTFA от отправки реплики (`ui.first_audio`). */
  audioStarted(turn: string): void {
    const ms = this.#audioProbe.started(turn);
    if (ms !== null) this.store.recordSpan(FIRST_AUDIO_SPAN, ms);
  }

  /** Реплика пользователя: в историю сразу (T-17), ядру — новым ходом. */
  say(text: string): void {
    const trimmed = text.trim();
    if (trimmed === "") {
      return;
    }
    this.store.addUserMessage(trimmed);
    // Новая реплика перебивает голос сразу — как ход в ядре (`new_message`), без ожидания сети.
    this.#cancel(null);
    this.#probe.sent();
    this.#audioProbe.sent();
    this.#transport.send({ v: PROTOCOL_VERSION, type: "chat.send", data: { text: trimmed } });
  }

  stop(): void {
    // Звук глушится сразу, не дожидаясь `turn.cancelled`: ход мог уже закончиться в ядре, а
    // голос ещё звучит (синтез быстрее реального времени).
    this.#cancel(null);
    this.#transport.send({ v: PROTOCOL_VERSION, type: "chat.cancel", data: {} });
  }
}
