/**
 * WebSocket-клиент ядра: переподключение с экспоненциальной паузой, очередь исходящих на время
 * разрыва, разбор кадров (frames.ts). Состояние приложения не трогает — только сообщает
 * слушателю (`TransportListener`).
 */
import { decodeAudioFrame, FrameError, parseMessage, type AudioFrame } from "./frames";
import type { InboundMessage, OutboundMessage } from "./protocol.gen";

/** Код закрытия «вытеснен новым клиентом» — `gateway/server.py` (ADR-0008). */
export const CLOSE_REPLACED = 4000;
const CLOSE_NORMAL = 1000;

/** Часть WebSocket, нужная транспорту: в тестах подменяется фейком. */
export interface SocketLike {
  binaryType: BinaryType;
  onopen: ((event: Event) => void) | null;
  onmessage: ((event: MessageEvent) => void) | null;
  onclose: ((event: CloseEvent) => void) | null;
  onerror: ((event: Event) => void) | null;
  send(data: string): void;
  close(code?: number, reason?: string): void;
}

export type SocketFactory = (url: string) => SocketLike;

/** `replaced` — ядро приняло другое окно; переподключаться нельзя, иначе окна вытесняют друг друга. */
export type ConnectionState = "connecting" | "open" | "closed" | "replaced";

export interface TransportListener {
  message(message: OutboundMessage): void;
  audio(frame: AudioFrame): void;
  connection(state: ConnectionState): void;
  protocolError(reason: string): void;
}

/** Пауза перед попыткой n (с нуля): `min(maxMs, initialMs · factor^n)`. */
export interface Backoff {
  initialMs: number;
  maxMs: number;
  factor: number;
}

export interface TransportOptions {
  url: string;
  backoff: Backoff;
  /** Сколько исходящих держать на время разрыва; при переполнении теряются старые. */
  queueLimit: number;
  socketFactory?: SocketFactory;
}

type Incoming =
  { kind: "message"; message: OutboundMessage } | { kind: "audio"; frame: AudioFrame };

function decodeIncoming(data: unknown): Incoming {
  if (typeof data === "string") {
    return { kind: "message", message: parseMessage(data) };
  }
  if (data instanceof ArrayBuffer) {
    return { kind: "audio", frame: decodeAudioFrame(data) };
  }
  throw new FrameError("Кадр ядра неизвестного вида");
}

const browserSocket: SocketFactory = (url) => new WebSocket(url);

export class Transport {
  readonly #options: TransportOptions;
  readonly #listener: TransportListener;
  readonly #factory: SocketFactory;
  readonly #queue: InboundMessage[] = [];
  #socket: SocketLike | null = null;
  #open = false;
  #running = false;
  #attempt = 0;
  #timer: ReturnType<typeof setTimeout> | null = null;

  constructor(options: TransportOptions, listener: TransportListener) {
    this.#options = options;
    this.#listener = listener;
    this.#factory = options.socketFactory ?? browserSocket;
  }

  /** Подключиться и держать связь до `stop()`. */
  start(): void {
    if (this.#running) {
      return;
    }
    this.#running = true;
    this.#attempt = 0;
    this.#connect();
  }

  /** Закрыть связь без переподключения; очередь исходящих отбрасывается. */
  stop(): void {
    this.#running = false;
    this.#cancelRetry();
    this.#queue.length = 0;
    const socket = this.#detach();
    if (socket !== null) {
      socket.close(CLOSE_NORMAL);
      this.#listener.connection("closed");
    }
  }

  /**
   * Отправить сообщение; при разрыве — в очередь до переподключения. `chat.cancel` в очередь
   * не встаёт: разрыв сам отменяет ход на ядре (T-14), а поздний «стоп» оборвал бы следующий.
   * `input.typing` — тоже: устаревший черновик после переподключения только занял бы LLM.
   */
  send(message: InboundMessage): void {
    if (this.#socket !== null && this.#open) {
      this.#socket.send(JSON.stringify(message));
      return;
    }
    if (message.type === "chat.cancel" || message.type === "input.typing") {
      return;
    }
    if (this.#queue.length >= this.#options.queueLimit) {
      this.#queue.shift();
    }
    this.#queue.push(message);
  }

  #connect(): void {
    this.#timer = null;
    this.#listener.connection("connecting");
    const socket = this.#factory(this.#options.url);
    socket.binaryType = "arraybuffer";
    socket.onopen = () => {
      this.#opened();
    };
    socket.onmessage = (event) => {
      this.#receive(event.data);
    };
    socket.onclose = (event) => {
      this.#closed(event.code);
    };
    // За ошибкой WebSocket всегда следует close — переподключение решается там.
    socket.onerror = null;
    this.#socket = socket;
  }

  #opened(): void {
    this.#open = true;
    this.#attempt = 0;
    this.#listener.connection("open");
    for (const message of this.#queue.splice(0)) {
      this.send(message);
    }
  }

  #receive(data: unknown): void {
    let incoming: Incoming;
    try {
      incoming = decodeIncoming(data);
    } catch (error) {
      if (error instanceof FrameError) {
        this.#listener.protocolError(error.message);
        return;
      }
      throw error;
    }
    if (incoming.kind === "message") {
      this.#listener.message(incoming.message);
    } else {
      this.#listener.audio(incoming.frame);
    }
  }

  #closed(code: number): void {
    this.#detach();
    if (!this.#running) {
      return;
    }
    if (code === CLOSE_REPLACED) {
      this.#running = false;
      this.#listener.connection("replaced");
      return;
    }
    this.#listener.connection("closed");
    this.#timer = setTimeout(() => {
      this.#connect();
    }, this.#nextDelay());
  }

  #nextDelay(): number {
    const { initialMs, maxMs, factor } = this.#options.backoff;
    const delay = Math.min(maxMs, initialMs * factor ** this.#attempt);
    this.#attempt += 1;
    return delay;
  }

  #cancelRetry(): void {
    if (this.#timer !== null) {
      clearTimeout(this.#timer);
      this.#timer = null;
    }
  }

  /** Отвязать обработчики: события старого сокета не должны трогать новое соединение. */
  #detach(): SocketLike | null {
    const socket = this.#socket;
    if (socket !== null) {
      socket.onopen = null;
      socket.onmessage = null;
      socket.onclose = null;
    }
    this.#socket = null;
    this.#open = false;
    return socket;
  }
}
