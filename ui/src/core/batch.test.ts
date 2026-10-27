import { describe, expect, it } from "vitest";

import { FrameBatch } from "./batch";

describe("FrameBatch", () => {
  it("один запрос кадра на пачку, изменения — по порядку", () => {
    const scheduled: (() => void)[] = [];
    const batch = new FrameBatch((callback) => scheduled.push(callback));
    const log: number[] = [];
    for (let i = 0; i < 5; i += 1) {
      batch.run(() => log.push(i));
    }
    expect(scheduled).toHaveLength(1);
    expect(log).toEqual([]);
    scheduled[0]?.();
    expect(log).toEqual([0, 1, 2, 3, 4]);

    batch.run(() => log.push(5));
    expect(scheduled).toHaveLength(2);
    scheduled[1]?.();
    expect(log).toEqual([0, 1, 2, 3, 4, 5]);
  });

  it("изменение, пришедшее во время применения пачки, ждёт следующего кадра", () => {
    const scheduled: (() => void)[] = [];
    const batch = new FrameBatch((callback) => scheduled.push(callback));
    const log: string[] = [];
    batch.run(() => {
      log.push("a");
      batch.run(() => log.push("b"));
    });
    scheduled[0]?.();
    expect(log).toEqual(["a"]);
    scheduled[1]?.();
    expect(log).toEqual(["a", "b"]);
  });
});
