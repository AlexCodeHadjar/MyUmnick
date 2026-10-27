import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AUDIO_HEADER_SIZE, type AudioFrame } from "./frames";
import type { InboundMessage, OutboundMessage } from "./protocol.gen";
import {
  CLOSE_REPLACED,
  Transport,
  type ConnectionState,
  type SocketLike,
  type TransportListener,
} from "./transport";

class FakeSocket implements SocketLike {
  binaryType: BinaryType = "blob";
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  readonly sent: string[] = [];
  closedWith: number | undefined = undefined;

  constructor(readonly url: string) {}

  send(data: string): void {
    this.sent.push(data);
  }

  close(code?: number): void {
    this.closedWith = code;
  }

  open(): void {
    this.onopen?.(new Event("open"));
  }

  receive(data: unknown): void {
    this.onmessage?.(new MessageEvent("message", { data }));
  }

  drop(code = 1006): void {
    this.onclose?.(new CloseEvent("close", { code }));
  }
}

class Recorder implements TransportListener {
  readonly messages: OutboundMessage[] = [];
  readonly frames: AudioFrame[] = [];
  readonly states: ConnectionState[] = [];
  readonly errors: string[] = [];

  message(message: OutboundMessage): void {
    this.messages.push(message);
  }

  audio(frame: AudioFrame): void {
    this.frames.push(frame);
  }

  connection(state: ConnectionState): void {
    this.states.push(state);
  }

  protocolError(reason: string): void {
    this.errors.push(reason);
  }
}

const SEND: InboundMessage = { v: 1, type: "chat.send", data: { text: "привет" } };
const CANCEL: InboundMessage = { v: 1, type: "chat.cancel", data: {} };

let sockets: FakeSocket[];
let recorder: Recorder;

function makeTransport(queueLimit = 4): Transport {
  return new Transport(
    {
      url: "ws://127.0.0.1:8765",
      backoff: { initialMs: 100, maxMs: 1000, factor: 2 },
      queueLimit,
      socketFactory: (url) => {
        const socket = new FakeSocket(url);
        sockets.push(socket);
        return socket;
      },
    },
    recorder,
  );
}

function last(): FakeSocket {
  const socket = sockets.at(-1);
  if (socket === undefined) {
    throw new Error("сокет не создан");
  }
  return socket;
}

beforeEach(() => {
  vi.useFakeTimers();
  sockets = [];
  recorder = new Recorder();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("подключение", () => {
  it("открывает сокет с бинарными кадрами в ArrayBuffer", () => {
    const transport = makeTransport();
    transport.start();
    transport.start();
    expect(sockets).toHaveLength(1);
    expect(last().url).toBe("ws://127.0.0.1:8765");
    expect(last().binaryType).toBe("arraybuffer");
    last().open();
    expect(recorder.states).toEqual(["connecting", "open"]);
  });

  it("разбирает текстовые и бинарные кадры", () => {
    const transport = makeTransport();
    transport.start();
    last().open();
    last().receive('{"v": 1, "type": "turn.started", "turn": "t-000001", "data": {}}');
    const buffer = new ArrayBuffer(AUDIO_HEADER_SIZE + 2);
    new DataView(buffer).setUint8(0, 0x01);
    new DataView(buffer).setUint8(1, 1);
    last().receive(buffer);
    expect(recorder.messages.map((m) => m.type)).toEqual(["turn.started"]);
    expect(recorder.frames).toHaveLength(1);
  });

  it("битый кадр — protocolError, связь живёт", () => {
    const transport = makeTransport();
    transport.start();
    last().open();
    last().receive("{не json");
    last().receive(new ArrayBuffer(3));
    last().receive(42);
    expect(recorder.errors).toHaveLength(3);
    expect(recorder.messages).toEqual([]);
    last().receive('{"v": 1, "type": "status", "data": {"component": "llm", "state": "ready"}}');
    expect(recorder.messages).toHaveLength(1);
  });

  it("ошибка слушателя не глотается", () => {
    const transport = makeTransport();
    transport.start();
    last().open();
    vi.spyOn(recorder, "message").mockImplementation(() => {
      throw new Error("баг в store");
    });
    expect(() => {
      last().receive('{"v": 1, "type": "turn.finished", "turn": "t-1", "data": {}}');
    }).toThrow("баг в store");
  });
});

describe("переподключение", () => {
  it("пауза растёт экспоненциально до потолка", () => {
    const transport = makeTransport();
    transport.start();
    const delays = [100, 200, 400, 800, 1000, 1000];
    for (const delay of delays) {
      last().drop();
      const before = sockets.length;
      vi.advanceTimersByTime(delay - 1);
      expect(sockets).toHaveLength(before);
      vi.advanceTimersByTime(1);
      expect(sockets).toHaveLength(before + 1);
    }
  });

  it("после успешного подключения пауза сбрасывается", () => {
    const transport = makeTransport();
    transport.start();
    last().drop();
    vi.advanceTimersByTime(100);
    last().drop();
    vi.advanceTimersByTime(200);
    last().open();
    last().drop();
    vi.advanceTimersByTime(100);
    expect(sockets).toHaveLength(4);
    expect(recorder.states.filter((s) => s === "closed")).toHaveLength(3);
  });

  it("вытеснение другим окном (4000) — без переподключения", () => {
    const transport = makeTransport();
    transport.start();
    last().open();
    last().drop(CLOSE_REPLACED);
    vi.advanceTimersByTime(10_000);
    expect(sockets).toHaveLength(1);
    expect(recorder.states.at(-1)).toBe("replaced");
  });

  it("stop() закрывает сокет и отменяет переподключение", () => {
    const transport = makeTransport();
    transport.start();
    last().open();
    transport.stop();
    expect(last().closedWith).toBe(1000);
    expect(last().onclose).toBeNull();
    expect(recorder.states.at(-1)).toBe("closed");

    transport.start();
    last().drop();
    transport.stop();
    vi.advanceTimersByTime(10_000);
    expect(sockets).toHaveLength(2);
  });

  it("события старого сокета после разрыва игнорируются", () => {
    const transport = makeTransport();
    transport.start();
    const old = last();
    old.open();
    old.drop();
    expect(old.onmessage).toBeNull();
    expect(old.onopen).toBeNull();
  });
});

describe("исходящие", () => {
  it("при связи уходят сразу", () => {
    const transport = makeTransport();
    transport.start();
    last().open();
    transport.send(SEND);
    expect(last().sent.map((raw): unknown => JSON.parse(raw))).toEqual([SEND]);
  });

  it("при разрыве копятся и уходят после подключения; стоп не копится", () => {
    const transport = makeTransport();
    transport.send(SEND);
    transport.send(CANCEL);
    transport.start();
    transport.send(SEND);
    expect(last().sent).toEqual([]);
    last().open();
    expect(last().sent).toHaveLength(2);
    expect(last().sent.every((raw) => raw.includes("chat.send"))).toBe(true);
  });

  it("очередь ограничена: теряются старые", () => {
    const transport = makeTransport(2);
    for (const text of ["1", "2", "3"]) {
      transport.send({ v: 1, type: "chat.send", data: { text } });
    }
    transport.start();
    last().open();
    const texts = last().sent.map((raw): unknown => JSON.parse(raw));
    expect(texts).toEqual([
      { v: 1, type: "chat.send", data: { text: "2" } },
      { v: 1, type: "chat.send", data: { text: "3" } },
    ]);
  });

  it("stop() отбрасывает очередь", () => {
    const transport = makeTransport();
    transport.send(SEND);
    transport.stop();
    transport.start();
    last().open();
    expect(last().sent).toEqual([]);
  });
});
