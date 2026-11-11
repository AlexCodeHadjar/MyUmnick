/**
 * Точка входа фич в ядро: store для чтения состояния и действия пользователя. Фичи не держат
 * транспорт сами (R-63) — так связь, очередь и переподключение живут в одном месте.
 */
import { locale } from "./i18n";
import { animationFrame, FrameBatch, type FrameScheduler } from "./batch";
import { encodeMicFrame, type AudioFrame } from "./frames";
import { FIRST_AUDIO_SPAN, FIRST_CHAR_SPAN, FirstAudioProbe, FirstCharProbe } from "./probe";
import { PROTOCOL_VERSION, type ChatActionData, type ImageData } from "./protocol.gen";
import { AppStore, type SpeechProgress } from "./store.svelte";
import { Transport, type Backoff, type SocketFactory } from "./transport";

/** 250 мс → ×2 → потолок 5 с: ядро на localhost поднимается за секунды, чаще стучаться незачем. */
const BACKOFF: Backoff = { initialMs: 250, maxMs: 5000, factor: 2 };
/** Реплики, набранные за время разрыва; больше — уже не диалог, а пачка устаревших сообщений. */
const QUEUE_LIMIT = 16;
/** Картинку можно отправить и без слов. */

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
  /** Зов по имени — мимо пачки: скрытое окно кадров не рисует, а открыться должно (ADR-0041). */
  #called: () => void = () => undefined;
  #micSeq = 0;
  #hidden = false;
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
          if (message.type === "input.barge_in") {
            this.#cancel(null);
            this.#called();
          }
          if (message.type === "input.final") {
            // Голосовая реплика — как `say()`: замеры идут от неё.
            probe.sent();
            audioProbe.sent();
          }
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
          // Ядро считает новое окно видимым, а скрытое должно сказать о себе само.
          if (state === "open" && this.#hidden) this.#sendVisibility();
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

  /** Витюбера позвали (в режиме `by_name` — по имени); окно в трее открывается. */
  onCalled(sink: () => void): void {
    this.#called = sink;
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
  say(text: string, attached?: { image: ImageData; preview: string }): void {
    const trimmed =
      text.trim() === "" && attached !== undefined ? locale.t.chat.imageOnly : text.trim();
    if (trimmed === "") {
      return;
    }
    this.store.addUserMessage(trimmed, attached?.preview);
    // Новая реплика перебивает голос сразу — как ход в ядре (`new_message`), без ожидания сети.
    this.#cancel(null);
    this.#probe.sent();
    this.#audioProbe.sent();
    if (attached === undefined) {
      this.#transport.send({ v: PROTOCOL_VERSION, type: "chat.send", data: { text: trimmed } });
    } else {
      this.#transport.send({
        v: PROTOCOL_VERSION,
        type: "chat.send_image",
        data: { text: trimmed, image: attached.image },
      });
    }
  }

  /** Кадр микрофона (Этап 11): только при связи, очереди нет. */
  micFrame(pcm: Int16Array, sampleRate: number): void {
    this.#transport.sendBinary(encodeMicFrame(this.#micSeq, sampleRate, pcm));
    this.#micSeq += 1;
  }

  /** Черновик реплики (с дебаунсом — у вызывающего): ядро греет кэш LLM, T-05. */
  typing(text: string): void {
    this.#transport.send({ v: PROTOCOL_VERSION, type: "input.typing", data: { text } });
  }

  /** Окно свернули или вернули: скрытому персонаж сам не заговорит (S-15.1). */
  setWindowVisible(visible: boolean): void {
    this.#hidden = !visible;
    this.#sendVisibility();
  }

  #sendVisibility(): void {
    const data = { visible: !this.#hidden };
    this.#transport.send({ v: PROTOCOL_VERSION, type: "window.visibility", data });
  }

  /** Панель ресурсов открыли или закрыли: снимки идут только при открытой. */
  watchResources(enabled: boolean): void {
    this.#transport.send({ v: PROTOCOL_VERSION, type: "resources.watch", data: { enabled } });
    if (!enabled) {
      this.store.resources = null;
    }
  }

  /** Согласие на загрузку в мастере первого запуска: только по действию пользователя. */
  installSetup(itemIds: string[], voice: string): void {
    this.store.setupResult = null;
    this.#transport.send({
      v: PROTOCOL_VERSION,
      type: "setup.install",
      data: { item_ids: itemIds, voice },
    });
  }

  cancelSetup(): void {
    this.#transport.send({ v: PROTOCOL_VERSION, type: "setup.cancel", data: {} });
  }

  /** Приватный режим: состояние вернётся от ядра, индикатор показывает то, что есть на самом деле. */
  setPrivate(enabled: boolean): void {
    this.#transport.send({ v: PROTOCOL_VERSION, type: "privacy.set", data: { enabled } });
  }

  /** Очистка памяти: вызывается только после подтверждения в интерфейсе. */
  eraseMemory(): void {
    this.store.privacy.result = null;
    this.#transport.send({ v: PROTOCOL_VERSION, type: "memory.erase", data: { confirm: true } });
  }

  /** Панель памяти открыта: нужен список фактов. */
  /** Действие со списком чатов (Этап 21): ответ — новый `store.chats`. */
  chatAction(data: Pick<ChatActionData, "action"> & Partial<ChatActionData>): void {
    const full: ChatActionData = { id: null, name: null, category: null, ...data };
    this.#transport.send({ v: PROTOCOL_VERSION, type: "chats.action", data: full });
  }

  /** Перенести факты в другое издание (S-20.10); итог — `store.transfer`. */
  transferMemory(): void {
    this.store.transfer = { state: "running", count: null, problem: null };
    this.#transport.send({ v: PROTOCOL_VERSION, type: "memory.transfer", data: {} });
  }

  listMemory(): void {
    this.#transport.send({ v: PROTOCOL_VERSION, type: "memory.list", data: {} });
  }

  saveFact(note: string, text: string): void {
    this.#transport.send({ v: PROTOCOL_VERSION, type: "memory.fact_save", data: { note, text } });
  }

  deleteFact(note: string): void {
    this.#transport.send({ v: PROTOCOL_VERSION, type: "memory.fact_delete", data: { note } });
  }

  /** Вернуться к реплике; следующая реплика начнёт новую ветку. Звук старого ответа не нужен. */
  goToTurn(turn: string): void {
    this.#cancel(null);
    this.#transport.send({ v: PROTOCOL_VERSION, type: "branch.go", data: { turn } });
  }

  saveCheckpoint(name: string): void {
    this.#transport.send({ v: PROTOCOL_VERSION, type: "branch.checkpoint", data: { name } });
  }

  stop(): void {
    // Звук глушится сразу, не дожидаясь `turn.cancelled`: ход мог уже закончиться в ядре, а
    // голос ещё звучит (синтез быстрее реального времени).
    this.#cancel(null);
    this.#transport.send({ v: PROTOCOL_VERSION, type: "chat.cancel", data: {} });
  }
}
