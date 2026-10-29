import { describe, expect, it } from "vitest";

import { NOD_DEGREES, NOD_MS, nodAngle } from "./nod";

describe("nodAngle", () => {
  it("вниз до полной глубины в середине и обратно к нулю", () => {
    expect(nodAngle(0)).toBeCloseTo(0);
    expect(nodAngle(NOD_MS / 2)).toBeCloseTo(-NOD_DEGREES);
    expect(nodAngle(NOD_MS - 1)).toBeGreaterThan(-0.1);
  });

  it("вне кивка — ноль", () => {
    expect(nodAngle(-5)).toBe(0);
    expect(nodAngle(NOD_MS)).toBe(0);
    expect(nodAngle(10_000)).toBe(0);
  });
});
