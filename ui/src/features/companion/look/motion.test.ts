import { describe, expect, it } from "vitest";

import type { Body } from "../body";
import { Motion } from "./motion";
import { LOOP_FPS, loopIndex } from "./pack";

const body: Body = {
  phase: "rest",
  x: 100,
  y: 100,
  pose: "stand",
  facing: 1,
  scale: 1,
  petting: 0,
  effects: [],
};

describe("плавность кодом", () => {
  it("спокойный цикл — туда-обратно без скачка 4→1; походка — кольцом", () => {
    const fps = LOOP_FPS.stand ?? 6;
    const at = (pose: "stand" | "walk", step: number): number =>
      loopIndex(pose, step / fps + 0.01, 4);
    expect([0, 1, 2, 3, 4, 5, 6].map((i) => at("stand", i))).toEqual([0, 1, 2, 3, 2, 1, 0]);
    expect([0, 1, 2, 3, 4].map((i) => loopIndex("walk", i / 10 + 0.01, 4))).toEqual([
      0, 1, 2, 3, 0,
    ]);
  });

  it("разворот — через узкую фигуру, а не мгновенное зеркало; посадка — упругая", () => {
    const motion = new Motion();
    motion.step(body, 0.016);
    const mid = [0.016, 0.016, 0.016, 0.016, 0.016].map(() =>
      motion.step({ ...body, facing: -1 }, 0.016),
    );
    expect(mid.some((p) => Math.abs(p.scaleX) < 0.9)).toBe(true);
    expect(motion.busy).toBe(true);
    for (let i = 0; i < 30; i += 1) motion.step({ ...body, facing: -1 }, 0.016);
    expect(motion.step({ ...body, facing: -1 }, 0.016).scaleX).toBeCloseTo(-1);
    motion.step({ ...body, facing: -1, phase: "fall" }, 0.016);
    const landed = motion.step({ ...body, facing: -1 }, 0.05);
    expect(landed.scaleY).toBeLessThan(1);
  });
});
