import { describe, expect, it } from "vitest";

import type { Surface } from "./anchors";
import { fitScreen } from "./room";

const MONITOR = { x: 0, y: 0, w: 1920, h: 1080 };
const FIGURE = 300;

describe("опоры в пределах экрана", () => {
  it("окно у верха — не сиденье; у бока окна там стоять нельзя, только висеть", () => {
    const list: Surface[] = [
      { kind: "edge", host: 1, x0: 400, x1: 900, y: 40 },
      { kind: "side", host: 1, x: 900, y0: 48, y1: 280, side: "right" },
    ];
    const fit = fitScreen(list, MONITOR, FIGURE);
    expect(fit.some((one) => one.kind === "edge")).toBe(false);
    const side = fit.find((one) => one.kind === "side");
    expect(side?.kind === "side" ? side.y1 - side.y0 : -1).toBeLessThan(60);
  });

  it("окно у левого края экрана: место у его левого бока за экраном — убрано", () => {
    const list: Surface[] = [{ kind: "side", host: 1, x: 10, y0: 400, y1: 640, side: "left" }];
    expect(fitScreen(list, MONITOR, FIGURE)).toEqual([]);
  });
});
