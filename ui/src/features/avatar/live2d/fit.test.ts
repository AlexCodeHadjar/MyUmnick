import { describe, expect, it } from "vitest";

import { applyFrame, fitModel, FIT_MARGIN, gazeAt } from "./fit";

describe("fitModel", () => {
  it("вписывает по узкой стороне с полями, центр сцены", () => {
    const room = 1 - 2 * FIT_MARGIN;
    expect(fitModel({ width: 1000, height: 2000 }, { width: 800, height: 1000 })).toEqual({
      scale: (1000 * room) / 2000,
      x: 400,
      y: 500,
    });
    expect(fitModel({ width: 1000, height: 500 }, { width: 800, height: 1000 }).scale).toBe(
      (800 * room) / 1000,
    );
  });

  it("пустая модель или сцена — масштаб 0, без NaN", () => {
    expect(fitModel({ width: 0, height: 0 }, { width: 800, height: 600 }).scale).toBe(0);
    expect(fitModel({ width: 100, height: 100 }, { width: 0, height: 0 }).scale).toBe(0);
  });
});

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

describe("applyFrame", () => {
  it("масштаб умножается, центр сдвигается в долях сцены", () => {
    const placed = applyFrame(
      { scale: 0.5, x: 400, y: 300 },
      { width: 800, height: 600 },
      {
        zoom: 2,
        offsetX: -0.1,
        offsetY: 0.3,
      },
    );
    expect(placed.scale).toBe(1);
    expect(placed.x).toBeCloseTo(320);
    expect(placed.y).toBeCloseTo(480);
  });
});
