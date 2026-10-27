import { describe, expect, it } from "vitest";

import { AUDIO_HEADER_SIZE, decodeAudioFrame, FrameError, parseMessage, turnRef } from "./frames";
import type { OutboundMessage } from "./protocol.gen";

/** Кадр как у `encode_audio_frame` в gateway/codec.py. */
function audioFrame(seq: number, rate: number, turn: bigint, samples: number[]): ArrayBuffer {
  const buffer = new ArrayBuffer(AUDIO_HEADER_SIZE + samples.length * 2);
  const view = new DataView(buffer);
  view.setUint8(0, 0x01);
  view.setUint8(1, 1);
  view.setUint16(2, seq, true);
  view.setUint32(4, rate, true);
  view.setBigUint64(8, turn, true);
  samples.forEach((sample, i) => {
    view.setInt16(AUDIO_HEADER_SIZE + i * 2, sample, true);
  });
  return buffer;
}

describe("decodeAudioFrame", () => {
  it("читает заголовок и PCM без копирования", () => {
    const buffer = audioFrame(65535, 24000, 42n, [0, 1, -1, 32767, -32768]);
    const frame = decodeAudioFrame(buffer);
    expect(frame.seq).toBe(65535);
    expect(frame.sampleRate).toBe(24000);
    expect(frame.turn).toBe("t-000042");
    expect(Array.from(frame.pcm)).toEqual([0, 1, -1, 32767, -32768]);
    expect(frame.pcm.buffer).toBe(buffer);
  });

  it("принимает кадр без PCM", () => {
    expect(decodeAudioFrame(audioFrame(0, 16000, 1n, [])).pcm.length).toBe(0);
  });

  it.each([
    ["короче заголовка", new ArrayBuffer(AUDIO_HEADER_SIZE - 1)],
    ["нечётный PCM", new ArrayBuffer(AUDIO_HEADER_SIZE + 3)],
  ])("отвергает кадр: %s", (_, buffer) => {
    const view = new DataView(buffer);
    if (buffer.byteLength >= 2) {
      view.setUint8(0, 0x01);
      view.setUint8(1, 1);
    }
    expect(() => decodeAudioFrame(buffer)).toThrow(FrameError);
  });

  it.each([
    [0, 0x02, 1],
    [1, 0x01, 2],
  ])("отвергает чужой тип или версию (#%i)", (_, kind, version) => {
    const buffer = audioFrame(0, 24000, 1n, [0]);
    new DataView(buffer).setUint8(0, kind);
    new DataView(buffer).setUint8(1, version);
    expect(() => decodeAudioFrame(buffer)).toThrow(FrameError);
  });
});

describe("turnRef", () => {
  it("совпадает с turn_ref ядра", () => {
    expect(turnRef(7n)).toBe("t-000007");
    expect(turnRef(1234567n)).toBe("t-1234567");
    expect(turnRef(2n ** 64n - 1n)).toBe("t-18446744073709551615");
  });
});

const SAMPLES: OutboundMessage[] = [
  { v: 1, type: "turn.started", turn: "t-000001", data: {} },
  { v: 1, type: "chat.delta", turn: "t-000001", data: { text: "Привет" } },
  { v: 1, type: "avatar.emotion", turn: "t-000001", data: { emotion: "happy", intensity: 1 } },
  { v: 1, type: "turn.finished", turn: "t-000001", data: {} },
  {
    v: 1,
    type: "turn.cancelled",
    turn: "t-000001",
    data: { reason: "user_stop", message: "" },
  },
  { v: 1, type: "metrics.span", turn: null, data: { name: "llm.ttft", ms: 120.5 } },
  { v: 1, type: "status", data: { component: "llm", state: "ready" } },
  { v: 1, type: "error", turn: null, data: { code: "bad_message", message: "битое" } },
];

describe("parseMessage", () => {
  it.each(SAMPLES.map((message) => [message.type, message] as const))(
    "принимает %s",
    (_, message) => {
      expect(parseMessage(JSON.stringify(message))).toEqual(message);
    },
  );

  it.each([
    ["не JSON", "{"],
    ["не объект", "[1, 2]"],
    ["null", "null"],
    ["чужая версия", '{"v": 2, "type": "status", "data": {}}'],
    ["неизвестный тип", '{"v": 1, "type": "chat.send", "data": {}}'],
    ["тип из прототипа", '{"v": 1, "type": "toString", "data": {}}'],
    ["data не объект", '{"v": 1, "type": "status", "data": 5}'],
    ["turn не строка", '{"v": 1, "type": "turn.started", "turn": 5, "data": {}}'],
  ])("отвергает: %s", (_, raw) => {
    expect(() => parseMessage(raw)).toThrow(FrameError);
  });
});
