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

  it("перебивание голосом глушит звук сразу, мимо пачки", () => {
    const { client, socket } = connected();
    const cancelled: (string | null)[] = [];
    client.onCancel((turn) => cancelled.push(turn));
    socket.receive(JSON.stringify({ v: 1, type: "input.barge_in", data: {} }));
    expect(cancelled).toEqual([null]);
  });

  it("снимок ресурсов — в store, закрытая панель его сбрасывает", () => {
    const { client, socket, frames } = connected();
    client.watchResources(true);
    expect(socket.sent).toEqual([{ v: 1, type: "resources.watch", data: { enabled: true } }]);
    const data = { limit_mb: 1, capacity_mb: 1, free_mb: 1, pinned: [], models: [] };
    socket.receive(JSON.stringify({ v: 1, type: "resources.snapshot", data }));
    frames.next();
    expect(client.store.resources).toEqual(data);
    client.watchResources(false);
    expect(client.store.resources).toBeNull();
  });

  it("мастер: загрузка только по явному вызову, итог — в store", () => {
    const { client, socket, frames } = connected();
    const data = {
      needed: true,
      gpu_total_mb: 16384,
      voices: ["xenia"],
      voice: "xenia",
      warnings: [],
      items: [],
    };
    socket.receive(JSON.stringify({ v: 1, type: "setup.state", data }));
    frames.next();
    expect(client.store.setup).toEqual(data);
    expect(socket.sent).toEqual([]);
    client.installSetup(["llm"], "xenia");
    expect(socket.sent).toEqual([
      { v: 1, type: "setup.install", data: { item_ids: ["llm"], voice: "xenia" } },
    ]);
    socket.receive(JSON.stringify({ v: 1, type: "setup.finished", data: { problem: null } }));
    frames.next();
    expect(client.store.setupResult).toEqual({ problem: null });
  });

  it("заблокированные реплики зрителей копятся с пределом", () => {
    const { client, socket, frames } = connected();
    for (let i = 0; i < 25; i += 1) {
      const data = { author: "враг", text: String(i) };
      socket.receive(JSON.stringify({ v: 1, type: "viewer.blocked", data }));
    }
    frames.next();
    expect(client.store.blockedViewers).toHaveLength(20);
    expect(client.store.blockedViewers.at(-1)?.text).toBe("24");
  });

  it("сообщение о компоненте показывается и уходит с новой репликой", () => {
    const { client, socket, frames } = connected();
    const data = { text: "Голос: снова работает" };
    socket.receive(JSON.stringify({ v: 1, type: "backend.notice", data }));
    frames.next();
    expect(client.store.notice).toBe("Голос: снова работает");
    client.say("привет");
    expect(client.store.notice).toBeNull();
  });

  it("приватный режим показывает то, что сказало ядро", () => {
    const { client, socket, frames } = connected();
    client.setPrivate(true);
    expect(client.store.privacy.enabled).toBe(false);
    expect(socket.sent).toEqual([{ v: 1, type: "privacy.set", data: { enabled: true } }]);
    const data = { enabled: true, erasable: true };
    socket.receive(JSON.stringify({ v: 1, type: "privacy.state", data }));
    frames.next();
    expect(client.store.privacy.enabled).toBe(true);
  });

  it("итог очистки памяти виден пользователю", () => {
    const { client, socket, frames } = connected();
    client.eraseMemory();
    expect(socket.sent).toEqual([{ v: 1, type: "memory.erase", data: { confirm: true } }]);
    socket.receive(JSON.stringify({ v: 1, type: "memory.erased", data: { problem: null } }));
    frames.next();
    expect(client.store.privacy.result).toBe("Память очищена");
  });

  it("редактор памяти: запросы и список", () => {
    const { client, socket, frames } = connected();
    client.listMemory();
    client.saveFact("n", "текст");
    client.deleteFact("n");
    expect(socket.sent).toEqual([
      { v: 1, type: "memory.list", data: {} },
      { v: 1, type: "memory.fact_save", data: { note: "n", text: "текст" } },
      { v: 1, type: "memory.fact_delete", data: { note: "n" } },
    ]);
    const fact = { note: "n", text: "т", source: "user", importance: 1, created: "2026-11-03" };
    const data = { facts: [fact], problem: null };
    socket.receive(JSON.stringify({ v: 1, type: "memory.facts", data }));
    frames.next();
    expect(client.store.memory.facts).toEqual([fact]);
  });

  it("dispose() закрывает связь", () => {
    const { client, frames } = connected();
    client.dispose();
    frames.next();
    expect(client.store.connection).toBe("closed");
  });
});
