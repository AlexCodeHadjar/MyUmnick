import { describe, expect, it } from "vitest";

import { gazeAt } from "./gaze";

describe("gazeAt", () => {
  const stage = { left: 100, top: 50, width: 400, height: 200 };

  it("центр — прямо, углы — по осям, y вверх", () => {
    expect(gazeAt(300, 150, stage)).toEqual([0, 0]);
    expect(gazeAt(500, 50, stage)).toEqual([1, 1]);
    expect(gazeAt(100, 250, stage)).toEqual([-1, -1]);
  });

  it("за пределами сцены — обрезка до края", () => {
    expect(gazeAt(5000, -5000, stage)).toEqual([1, 1]);
  });

  it("сцена нулевого размера — без деления на ноль", () => {
    const [x, y] = gazeAt(10, 10, { left: 0, top: 0, width: 0, height: 0 });
    expect(Number.isFinite(x) && Number.isFinite(y)).toBe(true);
  });
});
