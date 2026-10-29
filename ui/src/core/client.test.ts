import { describe, expect, it } from "vitest";

import { CoreClient } from "./client";
import { AUDIO_HEADER_SIZE, type AudioFrame } from "./frames";
import type { SocketLike } from "./transport";

class FakeSocket implements SocketLike {
  binaryType: BinaryType = "blob";
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  readonly sent: unknown[] = [];

  send(data: string): void {
    this.sent.push(JSON.parse(data));
  }

  close(): void {
    this.onclose?.(new CloseEvent("close", { code: 1000 }));
  }

  receive(data: unknown): void {
    this.onmessage?.(new MessageEvent("message", { data }));
  }
}

/** Ручные «кадры»: колбэки копятся, пока тест не вызовет `next()`. */
class Frames {
  readonly queued: (() => void)[] = [];
  readonly schedule = (callback: () => void): void => {
    this.queued.push(callback);
  };

  next(): void {
    for (const callback of this.queued.splice(0)) {
      callback();
    }
  }
}

function connected(): { client: CoreClient; socket: FakeSocket; frames: Frames } {
  const socket = new FakeSocket();
  const frames = new Frames();
  const client = new CoreClient({
    url: "ws://test",
    socketFactory: () => socket,
    scheduleFrame: frames.schedule,
  });
  client.start();
  socket.onopen?.(new Event("open"));
  frames.next();
  return { client, socket, frames };
}

const delta = (text: string): string =>
  JSON.stringify({ v: 1, type: "chat.delta", turn: "t-000003", data: { text } });

describe("CoreClient", () => {
  it("say(): реплика в историю сразу и ядру — chat.send", () => {
    const { client, socket } = connected();
    expect(client.store.connection).toBe("open");
    client.say("  привет  ");
    client.say("   ");
    expect(client.store.messages.map((m) => m.text)).toEqual(["привет"]);
    expect(socket.sent).toEqual([{ v: 1, type: "chat.send", data: { text: "привет" } }]);
  });

  it("typing() шлёт черновик ядру", () => {
    const { client, socket } = connected();
    client.typing("Расскажи");
    expect(socket.sent).toEqual([{ v: 1, type: "input.typing", data: { text: "Расскажи" } }]);
  });

  it("stop() шлёт chat.cancel", () => {
    const { client, socket } = connected();
    client.stop();
    expect(socket.sent).toEqual([{ v: 1, type: "chat.cancel", data: {} }]);
  });

  it("сообщения ядра применяются пачкой раз в кадр (T-16)", () => {
    const { client, socket, frames } = connected();
    socket.receive('{"v": 1, "type": "turn.started", "turn": "t-000003", "data": {}}');
    for (let i = 0; i < 100; i += 1) {
      socket.receive(delta(String(i % 10)));
    }
    expect(frames.queued).toHaveLength(1);
    expect(client.store.messages).toEqual([]);
    frames.next();
    expect(client.store.messages[0]?.text).toBe("0123456789".repeat(10));
    expect(frames.queued).toHaveLength(0);
  });

  it("разрыв встаёт в ту же очередь после уже пришедших сообщений", () => {
    const { client, socket, frames } = connected();
    socket.receive('{"v": 1, "type": "turn.started", "turn": "t-000003", "data": {}}');
    socket.receive(delta("Начало"));
    socket.close();
    frames.next();
    expect(client.store.connection).toBe("closed");
    expect(client.store.messages.map(({ text, status }) => [text, status])).toEqual([
      ["Начало", "cancelled"],
    ]);
  });

  it("аудио — сразу в приёмник, мимо пачки", () => {
    const { client, socket } = connected();
    const received: AudioFrame[] = [];
    client.onAudio((frame) => received.push(frame));
    const buffer = new ArrayBuffer(AUDIO_HEADER_SIZE);
    new DataView(buffer).setUint8(0, 0x01);
    new DataView(buffer).setUint8(1, 1);
    socket.receive(buffer);
    expect(received).toHaveLength(1);
  });

  it("замер UI: от say() до кадра с первым символом ответа", () => {
    const socket = new FakeSocket();
    const frames = new Frames();
    // say() засекает время для двух замеров (символ и звук), первый символ — третье чтение.
    const clock = [1000, 1000, 1042];
    const client = new CoreClient({
      url: "ws://test",
      socketFactory: () => socket,
      scheduleFrame: frames.schedule,
      now: () => clock.shift() ?? Number.NaN,
    });
    client.start();
    socket.onopen?.(new Event("open"));
    client.say("привет");
    socket.receive('{"v": 1, "type": "turn.started", "turn": "t-000003", "data": {}}');
    socket.receive(delta("П"));
    frames.next();
    expect(client.store.spans["ui.first_char"]).toEqual([42]);
  });

  it("отмена хода — плееру сразу, мимо пачки; разрыв — отмена всего звука", () => {
    const { client, socket } = connected();
    const cancelled: (string | null)[] = [];
    client.onCancel((turn) => cancelled.push(turn));
    socket.receive(
      JSON.stringify({
        v: 1,
        type: "turn.cancelled",
        turn: "t-000003",
        data: { reason: "user_stop", message: "" },
      }),
    );
    expect(cancelled).toEqual(["t-000003"]);
    socket.close();
    expect(cancelled).toEqual(["t-000003", null]);
  });

  it("стоп и новая реплика глушат голос сразу, не дожидаясь ядра", () => {
    const { client } = connected();
    const cancelled: (string | null)[] = [];
    client.onCancel((turn) => cancelled.push(turn));
    client.stop();
    client.say("ещё");
    expect(cancelled).toEqual([null, null]);
  });

  it("замер UI: от say() до звука ответа (ui.first_audio)", () => {
    const socket = new FakeSocket();
    const frames = new Frames();
    const clock = [1000, 1000, 1300];
    const client = new CoreClient({
      url: "ws://test",
      socketFactory: () => socket,
      scheduleFrame: frames.schedule,
      now: () => clock.shift() ?? Number.NaN,
    });
    client.start();
    socket.onopen?.(new Event("open"));
    client.say("привет");
    socket.receive('{"v": 1, "type": "turn.started", "turn": "t-000003", "data": {}}');
    client.audioStarted("t-000003");
    expect(client.store.spans["ui.first_audio"]).toEqual([300]);
  });

  it("что звучит — в store пачкой раз в кадр", () => {
    const { client, frames } = connected();
    const progress = { turn: "t-1", speaking: true, playedS: 0.5, receivedS: 2 };
    client.speech(progress);
    expect(client.store.voice.speech).toBeNull();
    frames.next();
    expect(client.store.voice.speech).toEqual(progress);
  });

  it("dispose() закрывает связь", () => {
    const { client, frames } = connected();
    client.dispose();
    frames.next();
    expect(client.store.connection).toBe("closed");
  });
});
