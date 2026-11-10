import { describe, expect, it } from "vitest";

import { buildSphere, fibonacciSphere, nearestEdges, ripple } from "./geometry";
import { EMOTION_HUE, mixHue, shimmerHue, sparkle } from "./palette";

describe("сфера из точек", () => {
  it("точки лежат на единичной сфере и покрывают оба полюса", () => {
    const points = fibonacciSphere(200);
    const ys: number[] = [];
    for (let i = 0; i < 200; i += 1) {
      const [x, y, z] = [points[i * 3] ?? 0, points[i * 3 + 1] ?? 0, points[i * 3 + 2] ?? 0];
      expect(Math.hypot(x, y, z)).toBeCloseTo(1, 5);
      ys.push(y);
    }
    expect(Math.max(...ys)).toBeGreaterThan(0.99);
    expect(Math.min(...ys)).toBeLessThan(-0.99);
  });

  it("рёбра без повторов и к соседям, а не через всю сферу", () => {
    const points = fibonacciSphere(120);
    const edges = nearestEdges(points, 3);
    const keys = new Set<string>();
    for (let e = 0; e < edges.length; e += 2) {
      const [a, b] = [edges[e] ?? 0, edges[e + 1] ?? 0];
      keys.add(a < b ? `${String(a)}-${String(b)}` : `${String(b)}-${String(a)}`);
      const dx = (points[a * 3] ?? 0) - (points[b * 3] ?? 0);
      expect(Math.abs(dx)).toBeLessThan(0.6);
    }
    expect(keys.size).toBe(edges.length / 2);
    expect(buildSphere(420, 3).edges.length / 2).toBeGreaterThan(420);
  });

  it("без голоса точки не вибрируют, с голосом — в пределах энергии, соседи — похоже", () => {
    expect(Math.abs(ripple(0, 0.5, 1, 2, 0.1) - ripple(0.01, 0.51, 1, 2, 0.1))).toBeLessThan(0.02);
    expect(ripple(0.2, 0.5, 0.8, 1.2, 0)).toBeCloseTo(0, 10);
    expect(Math.abs(ripple(0.2, 0.5, 0.8, 1.2, 0.1))).toBeLessThanOrEqual(0.1);
  });

  it("оттенок идёт по короткой дуге и переливается", () => {
    expect(mixHue(350, 10, 0.5)).toBeCloseTo(0, 5);
    expect(mixHue(EMOTION_HUE.neutral, EMOTION_HUE.angry, 0)).toBe(EMOTION_HUE.neutral);
    expect(shimmerHue(100, 0)).toBe(100);
    expect(sparkle(3, 0.5)).toBeGreaterThanOrEqual(0.55);
    expect(sparkle(3, 0.5)).toBeLessThanOrEqual(1);
  });
});
