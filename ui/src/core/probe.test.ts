import { describe, expect, it } from "vitest";

import { FirstAudioProbe, FirstCharProbe } from "./probe";
import type { OutboundMessage } from "./protocol.gen";

const started = (turn: string): OutboundMessage => ({ v: 1, type: "turn.started", turn, data: {} });
const delta = (turn: string, text: string): OutboundMessage => ({
  v: 1,
  type: "chat.delta",
  turn,
  data: { text },
});

function probeAt(times: number[]): FirstCharProbe {
  return new FirstCharProbe(() => times.shift() ?? Number.NaN);
}

describe("FirstCharProbe", () => {
  it("замер от отправки до первой непустой дельты нового хода — один раз", () => {
    const probe = probeAt([100, 160]);
    expect(probe.observe(delta("t-1", "до отправки"))).toBeNull();
    probe.sent();
    expect(probe.observe(delta("t-0", "хвост прошлого хода"))).toBeNull();
    expect(probe.observe(started("t-1"))).toBeNull();
    expect(probe.observe(delta("t-1", ""))).toBeNull();
    expect(probe.observe(delta("t-1", "П"))).toBe(60);
    expect(probe.observe(delta("t-1", "ривет"))).toBeNull();
  });

  it("ход закончился без текста — замер сбрасывается", () => {
    const probe = probeAt([0]);
    probe.sent();
    probe.observe(started("t-2"));
    probe.observe({
      v: 1,
      type: "turn.cancelled",
      turn: "t-2",
      data: { reason: "error", message: "" },
    });
    expect(probe.observe(delta("t-2", "поздно"))).toBeNull();
  });

  it("служебные сообщения не влияют", () => {
    const probe = probeAt([0, 5]);
    probe.sent();
    probe.observe(started("t-3"));
    expect(
      probe.observe({ v: 1, type: "status", data: { component: "llm", state: "ready" } }),
    ).toBeNull();
    probe.observe({ v: 1, type: "turn.finished", turn: "t-9", data: {} });
    expect(probe.observe(delta("t-3", "а"))).toBe(5);
  });
});

describe("FirstAudioProbe", () => {
  it("замер от отправки до звука нового хода — один раз", () => {
    const times = [100, 380];
    const probe = new FirstAudioProbe(() => times.shift() ?? Number.NaN);
    expect(probe.started("t-1")).toBeNull();
    probe.sent();
    probe.observe(started("t-1"));
    expect(probe.started("t-0")).toBeNull();
    expect(probe.started("t-1")).toBe(280);
    expect(probe.started("t-1")).toBeNull();
  });

  it("отменённый ход замер сбрасывает", () => {
    const probe = new FirstAudioProbe(() => 0);
    probe.sent();
    probe.observe(started("t-2"));
    probe.observe({
      v: 1,
      type: "turn.cancelled",
      turn: "t-2",
      data: { reason: "user_stop", message: "" },
    });
    expect(probe.started("t-2")).toBeNull();
  });
});
