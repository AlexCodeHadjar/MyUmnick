import { describe, expect, it } from "vitest";

import { bondTone, grow, parseBond, settle } from "./bond";

const DAY = 24 * 3_600_000;

describe("привязанность", () => {
  it("растёт от внимания, медленнее к вершине, не выше 1", () => {
    let bond = { level: 0.3, at: 0 };
    for (let i = 0; i < 400; i += 1) bond = grow(bond, "pet", i * 1000);
    expect(bond.level).toBeGreaterThan(0.9);
    expect(bond.level).toBeLessThanOrEqual(1);
    expect(bondTone(bond)).toBe("warm");
  });

  it("без внимания тает к стартовой: за неделю — наполовину", () => {
    const week = settle({ level: 0.9, at: 0 }, 7 * DAY);
    expect(week.level).toBeCloseTo(0.6, 2);
    expect(bondTone({ level: 0.1, at: 0 })).toBe("cool");
  });

  it("битое и чужое — стартовая", () => {
    expect(parseBond("{", 5)).toEqual({ level: 0.3, at: 5 });
    expect(parseBond(JSON.stringify({ level: 7, at: 0 }), 5).level).toBe(0.3);
  });
});
