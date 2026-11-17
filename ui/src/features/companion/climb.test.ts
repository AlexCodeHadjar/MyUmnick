import { describe, expect, it } from "vitest";

import { snap, surfaces } from "./anchors";
import { Brain } from "./brain";
import { climbRoute } from "./climb";
import type { World } from "./world";

/** Окно стоит на «полу» (низ = 1040): по его левому боку можно залезть с пола. */
const WORLD: World = {
  monitor: { x: 0, y: 0, w: 1920, h: 1080 },
  work: { x: 0, y: 0, w: 1920, h: 1040 },
  seats: [{ id: 7, rect: { x: 600, y: 500, w: 600, h: 540 }, open: [[600, 1200]] }],
  focus: { kind: "window", id: 7, app: "code" },
  fullscreen: false,
};

function ticks(brain: Brain, seconds: number, each?: (brain: Brain) => void): void {
  for (let t = 0; t < seconds; t += 0.016) {
    brain.tick(0.016);
    each?.(brain);
  }
}

describe("лазанье по стенам", () => {
  it("с пола на окно — идёт к боку, лезет лицом к стене, садится наверху", () => {
    const brain = new Brain(() => 0.5);
    brain.setWorld(WORLD);
    const floor = snap(brain.surfaceList, 450, 1040, 30);
    const top = snap(brain.surfaceList, 800, 500, 30);
    if (floor === null || top === null) throw new Error("нет опор");
    brain.place(floor);
    brain.goTo(top);
    expect(brain.phase).toBe("walk");
    const poses = new Set<string>();
    ticks(brain, 12, (b) => {
      if (b.phase === "climb") {
        poses.add(b.body().pose);
        expect(b.facing).toBe(1);
      }
    });
    expect(poses).toEqual(new Set(["climb"]));
    expect([brain.phase, brain.y]).toEqual(["rest", 500]);
  });

  it("низкое окно или окно в воздухе — без лазанья", () => {
    const list = surfaces(WORLD);
    const floor = snap(list, 450, 1040, 30);
    const top = snap(list, 800, 500, 30);
    if (floor === null || top === null) throw new Error("нет опор");
    expect(climbRoute(list, floor, top, 1040)).not.toBeNull();
    expect(climbRoute(list, floor, top, 700)).toBeNull();
    expect(climbRoute(list, { ...floor, y: 560 }, top, 1040)).toBeNull();
  });

  it("окно двигают, пока лезет, — лезет вместе с ним", () => {
    const brain = new Brain(() => 0.5);
    brain.setWorld(WORLD);
    const floor = snap(brain.surfaceList, 540, 1040, 30);
    const top = snap(brain.surfaceList, 800, 500, 30);
    if (floor === null || top === null) throw new Error("нет опор");
    brain.place(floor);
    brain.goTo(top);
    expect(brain.phase).toBe("climb");
    const x = brain.x;
    brain.hostMoved(7, { x: 650, y: 500, w: 600, h: 540 });
    expect(brain.x).toBe(x + 50);
  });
});
