import { describe, expect, it } from "vitest";

import { floorSpot, surfaces } from "./anchors";
import { Brain } from "./brain";
import { watching } from "./watch";
import type { World } from "./world";

const WORLD: World = {
  monitor: { x: 0, y: 0, w: 1920, h: 1080 },
  work: { x: 0, y: 0, w: 1920, h: 1040 },
  seats: [],
  focus: { kind: "window", id: 1, app: "chrome" },
  fullscreen: false,
};

describe("смотрим вместе", () => {
  it("видео: плеер, браузер на весь экран, вкладка видеосайта", () => {
    const base = { app: "chrome", topic: "browser" as const, fullscreen: false, tab: null };
    expect(watching({ ...base, app: "vlc", topic: "video" })).toBe(true);
    expect(watching({ ...base, app: "obs64", topic: "video" })).toBe(false);
    expect(watching({ ...base, fullscreen: true })).toBe(true);
    expect(watching({ ...base, tab: "Котики - YouTube" })).toBe(true);
    expect(watching({ ...base, tab: "Почта" })).toBe(false);
    expect(watching({ ...base, app: "code", topic: "code", fullscreen: true })).toBe(false);
  });

  it("в углу смотрит с попкорном, не засыпает и не гуляет", () => {
    const brain = new Brain(() => 0.5);
    brain.wander = true;
    brain.setWorld(WORLD);
    const corner = floorSpot(surfaces(WORLD), true);
    if (corner === null) throw new Error("нет угла");
    brain.place(corner);
    brain.watching = true;
    expect(brain.body().pose).toBe("watch");
    expect(brain.body().facing).toBe(-1);
    let popcorn = 0;
    for (let t = 0; t < 600; t += 0.05) {
      brain.tick(0.05);
      popcorn += brain
        .body()
        .effects.filter((one) => one.kind === "popcorn" && one.t < 0.06).length;
    }
    expect(popcorn).toBeGreaterThan(50);
    expect([brain.phase, brain.x, brain.body().pose]).toEqual(["rest", corner.x, "watch"]);
  });

  it("тихий режим (полный экран без видео) — сидит и не гуляет", () => {
    const brain = new Brain(() => 0.5);
    brain.wander = true;
    brain.setWorld(WORLD);
    const corner = floorSpot(surfaces(WORLD), true);
    if (corner === null) throw new Error("нет угла");
    brain.place(corner);
    brain.quiet = true;
    for (let t = 0; t < 120; t += 0.05) brain.tick(0.05);
    expect([brain.phase, brain.x]).toEqual(["rest", corner.x]);
  });
});
