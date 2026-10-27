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
}

function connected(): { client: CoreClient; socket: FakeSocket } {
  const socket = new FakeSocket();
  const client = new CoreClient({ url: "ws://test", socketFactory: () => socket });
  client.start();
  socket.onopen?.(new Event("open"));
  return { client, socket };
}

describe("CoreClient", () => {
  it("say(): реплика в историю сразу и ядру — chat.send", () => {
    const { client, socket } = connected();
    expect(client.store.connection).toBe("open");
    client.say("  привет  ");
    client.say("   ");
    expect(client.store.messages.map((m) => m.text)).toEqual(["привет"]);
    expect(socket.sent).toEqual([{ v: 1, type: "chat.send", data: { text: "привет" } }]);
  });

  it("stop() шлёт chat.cancel", () => {
    const { client, socket } = connected();
    client.stop();
    expect(socket.sent).toEqual([{ v: 1, type: "chat.cancel", data: {} }]);
  });

  it("сообщения ядра попадают в store, аудио — в подключённый приёмник", () => {
    const { client, socket } = connected();
    const frames: AudioFrame[] = [];
    client.onAudio((frame) => frames.push(frame));
    socket.onmessage?.(
      new MessageEvent("message", {
        data: '{"v": 1, "type": "turn.started", "turn": "t-000003", "data": {}}',
      }),
    );
    const buffer = new ArrayBuffer(AUDIO_HEADER_SIZE);
    new DataView(buffer).setUint8(0, 0x01);
    new DataView(buffer).setUint8(1, 1);
    socket.onmessage?.(new MessageEvent("message", { data: buffer }));
    expect(client.store.turn).toBe("t-000003");
    expect(frames).toHaveLength(1);
  });

  it("dispose() закрывает связь", () => {
    const { client } = connected();
    client.dispose();
    expect(client.store.connection).toBe("closed");
  });
});
