import { describe, expect, it } from "vitest";

import { isPlayerEvent } from "./events";

describe("isPlayerEvent", () => {
  it("принимает события процессора", () => {
    expect(isPlayerEvent({ type: "idle" })).toBe(true);
    expect(isPlayerEvent({ type: "started", tag: "t-1" })).toBe(true);
    expect(isPlayerEvent({ type: "progress", tag: "t-1", samples: 128 })).toBe(true);
  });

  it("отбрасывает чужое и битое", () => {
    expect(isPlayerEvent(null)).toBe(false);
    expect(isPlayerEvent("idle")).toBe(false);
    expect(isPlayerEvent({ type: "started" })).toBe(false);
    expect(isPlayerEvent({ type: "progress", tag: "t-1" })).toBe(false);
    expect(isPlayerEvent({ type: "boom", tag: "t-1" })).toBe(false);
  });
});
