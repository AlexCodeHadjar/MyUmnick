import { describe, expect, it } from "vitest";

import { MouthFollower, rms } from "./lipsync";

const cfg = { attackMs: 30, releaseMs: 90, gate: 0.02, fullAt: 0.2 };

describe("rms", () => {
  it("громкость блока; пустой — ноль", () => {
    expect(rms(new Float32Array(0))).toBe(0);
    expect(rms(Float32Array.from([0.5, -0.5, 0.5, -0.5]))).toBeCloseTo(0.5);
  });
});

describe("MouthFollower", () => {
  it("тишина и шум ниже порога рот не открывают", () => {
    const mouth = new MouthFollower(cfg);
    for (let i = 0; i < 60; i++) {
      mouth.update(0.015, 16);
    }
    expect(mouth.value).toBe(0);
  });

  it("громкая речь открывает рот почти полностью за ~4 постоянные атаки", () => {
    const mouth = new MouthFollower(cfg);
    for (let i = 0; i < 8; i++) {
      mouth.update(0.5, 16);
    }
    expect(mouth.value).toBeGreaterThan(0.95);
    expect(mouth.value).toBeLessThanOrEqual(1);
  });

  it("открывается быстрее, чем закрывается", () => {
    const mouth = new MouthFollower(cfg);
    const opened = mouth.update(0.2, 30);
    mouth.reset();
    mouth.update(0.2, 10_000);
    const closed = 1 - mouth.update(0, 30);
    expect(opened).toBeGreaterThan(closed);
  });

  it("не зависит от частоты кадров", () => {
    const fast = new MouthFollower(cfg);
    const slow = new MouthFollower(cfg);
    for (let i = 0; i < 4; i++) {
      fast.update(0.1, 8);
    }
    slow.update(0.1, 32);
    expect(fast.value).toBeCloseTo(slow.value, 6);
  });

  it("в паузе рот закрывается до нуля", () => {
    const mouth = new MouthFollower(cfg);
    mouth.update(0.3, 1000);
    for (let i = 0; i < 60; i++) {
      mouth.update(0, 16);
    }
    expect(mouth.value).toBeLessThan(0.01);
  });
});
