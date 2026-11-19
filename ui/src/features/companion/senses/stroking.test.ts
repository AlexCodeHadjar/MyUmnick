import { describe, expect, it } from "vitest";
import { CursorTouch } from "./stroking";

const box = { x: 100, y: 100, w: 100, h: 160 };
describe("cursor touch", () => {
  it("recognises repeated strokes within the figure", () => {
    const touch = new CursorTouch(() => 0);
    expect([120, 155, 125, 165, 125].map((x, i) => touch.feed(x, 180, i * 100, box))).toContain(
      "pet",
    );
  });
  it("ignores jitter and an interrupted stroke", () => {
    const touch = new CursorTouch(() => 0);
    for (const [i, x] of [120, 122, 121, 124, 120, 160, 128, 12, 162, 121].entries())
      expect(touch.feed(x, 180, i * 90, box)).not.toBe("pet");
  });
  it("reaches once when approaching from outside", () => {
    const touch = new CursorTouch(() => 0);
    touch.feed(400, 180, 0, box);
    touch.feed(255, 180, 50, box);
    expect(touch.feed(220, 180, 100, box)).toBe("reach");
    touch.feed(400, 180, 200, box);
    expect(touch.feed(225, 180, 300, box)).toBeNull();
  });
});
