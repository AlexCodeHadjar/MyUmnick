import { describe, expect, it } from "vitest";

import { Sanity, type Snapshot } from "./sanity";

const ok: Snapshot = {
  phase: "rest",
  x: 500,
  y: 800,
  screen: { x: 0, y: 0, w: 1536, h: 864 },
  shown: true,
  holding: false,
  activity: "idle",
};

function run(sanity: Sanity, from: number, to: number, s: Snapshot): string[] {
  const fixes: string[] = [];
  for (let t = from; t < to; t += 0.25) fixes.push(...sanity.observe(s, t));
  return fixes;
}

describe("сторож «Разума»", () => {
  it("в норме не вмешивается", () => {
    const sanity = new Sanity();
    expect(run(sanity, 0, 600, ok)).toEqual([]);
    expect(sanity.repairs).toBe(0);
  });

  it("NaN и вылет далеко за экран — на пол", () => {
    expect(run(new Sanity(), 0, 2, { ...ok, x: Number.NaN })).toContain("land");
    expect(run(new Sanity(), 0, 2, { ...ok, y: 5000 })).toContain("land");
  });

  it("падает дольше 6 с — ставит на опору; короткое падение — норма", () => {
    expect(run(new Sanity(), 0, 5, { ...ok, phase: "fall" })).toEqual([]);
    expect(run(new Sanity(), 0, 8, { ...ok, phase: "fall" })).toContain("land");
  });

  it("«держат», а мышь отпущена — отпускает; пропал при показе — выходит заново", () => {
    expect(run(new Sanity(), 0, 3, { ...ok, phase: "held", holding: false })).toContain("release");
    expect(run(new Sanity(), 0, 3, { ...ok, phase: "held", holding: true })).toEqual([]);
    expect(run(new Sanity(), 0, 5, { ...ok, phase: "hidden" })).toContain("arrive");
    expect(run(new Sanity(), 0, 5, { ...ok, phase: "hidden", shown: false })).toEqual([]);
  });

  it("застрял в портале — заканчивает: выход — на опору, уход — спрятаться", () => {
    expect(run(new Sanity(), 0, 6, { ...ok, phase: "portal_out" })).toContain("land");
    expect(run(new Sanity(), 0, 6, { ...ok, phase: "portal_in" })).toContain("hide");
  });

  it("метания и болтливость — успокаивает и глушит голос на время", () => {
    const sanity = new Sanity();
    const fixes: string[] = [];
    for (let i = 0; i < 20; i += 1) {
      fixes.push(...sanity.observe({ ...ok, activity: i % 2 === 0 ? "wander" : "chat" }, i * 2));
    }
    expect(fixes).toContain("calm");
    expect(sanity.calm(40)).toBe(true);
    for (let i = 0; i < 8; i += 1) sanity.noteLine(100 + i);
    expect(sanity.observe(ok, 110)).toContain("hush");
    expect(sanity.hushed(150)).toBe(true);
    expect(sanity.hushed(300)).toBe(false);
  });
});
