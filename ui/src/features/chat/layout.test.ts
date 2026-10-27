import { describe, expect, it } from "vitest";

import { computeWindow, isAtBottom, OVERSCAN_PX, STICK_TOLERANCE_PX } from "./layout";

interface Item {
  id: number;
  height: number;
}

const items = (count: number, height = 50): Item[] =>
  Array.from({ length: count }, (_, id) => ({ id, height }));
const heightOf = (item: Item): number => item.height;

describe("computeWindow", () => {
  it("1000 сообщений: в окне — только экран и запас", () => {
    const list = items(1000);
    const viewport = { scrollTop: 25_000, height: 700 };
    const view = computeWindow(list, heightOf, viewport);
    expect(view.totalHeight).toBe(50_000);
    expect(view.placed.length).toBeLessThanOrEqual((700 + 2 * OVERSCAN_PX) / 50 + 2);
    const first = view.placed[0];
    const last = view.placed.at(-1);
    expect(first?.top).toBeLessThanOrEqual(25_000 - OVERSCAN_PX);
    expect((last?.top ?? 0) + 50).toBeGreaterThanOrEqual(25_000 + 700 + OVERSCAN_PX - 50);
    view.placed.forEach(({ item, top }) => {
      expect(top).toBe(item.id * 50);
    });
  });

  it("раскладка 10 000 сообщений укладывается в бюджет кадра", () => {
    const list = items(10_000);
    const started = performance.now();
    for (let frame = 0; frame < 60; frame += 1) {
      computeWindow(list, heightOf, { scrollTop: frame * 1000, height: 700 });
    }
    const perFrame = (performance.now() - started) / 60;
    expect(perFrame).toBeLessThan(2);
  });

  it("разные высоты: позиции — сумма предыдущих", () => {
    const list = [10, 20, 30, 40].map((height, id) => ({ id, height }));
    const view = computeWindow(list, heightOf, { scrollTop: 0, height: 1000 });
    expect(view.placed.map((p) => p.top)).toEqual([0, 10, 30, 60]);
    expect(view.totalHeight).toBe(100);
  });

  it("начало и конец списка, пустой список", () => {
    const list = items(100);
    expect(computeWindow(list, heightOf, { scrollTop: 0, height: 300 }).placed[0]?.item.id).toBe(0);
    const end = computeWindow(list, heightOf, { scrollTop: 5000 - 300, height: 300 });
    expect(end.placed.at(-1)?.item.id).toBe(99);
    expect(computeWindow([], heightOf, { scrollTop: 0, height: 300 })).toEqual({
      placed: [],
      totalHeight: 0,
    });
  });

  it("прокрутка за пределы — пусто, без исключений", () => {
    const view = computeWindow(items(10), heightOf, { scrollTop: 10_000, height: 300 });
    expect(view.placed).toEqual([]);
  });
});

describe("isAtBottom", () => {
  it("внизу с допуском", () => {
    expect(isAtBottom({ scrollTop: 700, height: 300 }, 1000)).toBe(true);
    expect(isAtBottom({ scrollTop: 700 - STICK_TOLERANCE_PX, height: 300 }, 1000)).toBe(true);
    expect(isAtBottom({ scrollTop: 600, height: 300 }, 1000)).toBe(false);
    expect(isAtBottom({ scrollTop: 0, height: 300 }, 100)).toBe(true);
  });
});
