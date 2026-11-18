import { describe, expect, it } from "vitest";

import { cursorSpot, inTheWay, stepAside, surfaces, worthMoving, type World } from ".";

const MONITOR = { x: 0, y: 0, w: 1920, h: 1080 };
const WORLD: World = {
  monitor: MONITOR,
  work: { x: 0, y: 0, w: 1920, h: 1040 },
  seats: [],
  focus: { kind: "desktop" },
  fullscreen: false,
};
const LIST = surfaces(WORLD);
const FIGURE = 300;
const FEET = { x: 900, y: 1040 };

describe("за курсором", () => {
  it("курсор на уровне — идёт по полу к нему, не вставая под стрелку", () => {
    const spot = cursorSpot(LIST, { x: 1400, y: 900 }, FEET, MONITOR, FIGURE);
    expect(spot?.surface.kind).toBe("floor");
    expect(spot?.x).toBe(1310);
  });

  it("курсор высоко — лезет по краю экрана с его стороны", () => {
    const spot = cursorSpot(LIST, { x: 1700, y: 400 }, FEET, MONITOR, FIGURE);
    expect(spot?.surface.kind).toBe("side");
    expect(spot?.facing).toBe(-1);
  });

  it("курсор у верха — свисает с верхнего края", () => {
    const spot = cursorSpot(LIST, { x: 600, y: 40 }, FEET, MONITOR, FIGURE);
    expect(spot?.surface.kind).toBe("ceiling");
    expect(spot?.pose).toBe("hang_side");
  });

  it("мелкий сдвиг на той же опоре — не повод идти", () => {
    const here = cursorSpot(LIST, { x: 1000, y: 900 }, FEET, MONITOR, FIGURE);
    const there = cursorSpot(LIST, { x: 1050, y: 900 }, FEET, MONITOR, FIGURE);
    expect(here && there && worthMoving(here, there)).toBe(false);
  });
});

describe("не мешать печатать", () => {
  const caret = { x: 880, y: 960, w: 2, h: 18 };

  it("рядом с полем ввода — мешает, далеко — нет", () => {
    expect(inTheWay(caret, FEET, FIGURE)).toBe(true);
    expect(inTheWay(caret, { x: 1700, y: 1040 }, FIGURE)).toBe(false);
  });

  it("отходит по своей опоре так, чтобы не мешать", () => {
    const here = cursorSpot(LIST, { x: 990, y: 900 }, FEET, MONITOR, FIGURE);
    const next = stepAside(LIST, here, caret, FIGURE);
    expect(next).not.toBeNull();
    expect(next && inTheWay(caret, next, FIGURE, 40)).toBe(false);
  });
});
