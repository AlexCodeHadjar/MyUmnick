import { describe, expect, it } from "vitest";

import { gestureAngle, type GestureSpec } from "./gesture";

const TILT: GestureSpec = { axis: "roll", degrees: 10, ms: 1000, waves: 1 };
const SHAKE: GestureSpec = { axis: "yaw", degrees: 10, ms: 800, waves: 4 };

describe("жест", () => {
  it("начинается и кончается в покое", () => {
    expect(gestureAngle(TILT, 0)).toBeCloseTo(0);
    expect(gestureAngle(TILT, 999.9)).toBeCloseTo(0, 2);
    expect(gestureAngle(TILT, 1000)).toBe(0);
    expect(gestureAngle(TILT, -1)).toBe(0);
  });

  it("наклон доходит до размаха посередине", () => {
    expect(gestureAngle(TILT, 500)).toBeCloseTo(10);
  });

  it("покачивание идёт в обе стороны", () => {
    const samples = Array.from({ length: 80 }, (_, i) => gestureAngle(SHAKE, i * 10));
    expect(Math.max(...samples)).toBeGreaterThan(3);
    expect(Math.min(...samples)).toBeLessThan(-3);
  });
});
