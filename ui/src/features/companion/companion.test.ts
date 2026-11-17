import { describe, expect, it } from "vitest";

import { messagesFor } from "../../core";

import { below, floorSpot, seatSpot, snap, surfaces } from "./space";
import { Brain, WALK_LIMIT } from "./body";
import { bubbleText, followSpot, placeBubble, release, velocityOf } from "./space";
import { along, lightning, seeded } from "./look";
import { pickFrame, poseName, sequence } from "./look";
import { choosePoke, remark, topicOf } from "./senses";
import { DEFAULT_SETTINGS, parseSettings, shouldShow } from "./settings";
import { worldToCss, type World } from "./space";

const WORLD: World = {
  monitor: { x: 0, y: 0, w: 1920, h: 1080 },
  work: { x: 0, y: 0, w: 1920, h: 1040 },
  seats: [
    { id: 1, rect: { x: 200, y: 300, w: 800, h: 500 }, open: [[200, 1000]] },
    { id: 2, rect: { x: 1200, y: 200, w: 500, h: 400 }, open: [[1200, 1700]] },
  ],
  focus: { kind: "window", id: 1, app: "code" },
  fullscreen: false,
};
const LIST = surfaces(WORLD);

function settle(brain: Brain, seconds = 3): void {
  for (let t = 0; t < seconds; t += 0.016) brain.tick(0.016);
}

describe("опоры и позы", () => {
  it("верх окна — сидит, угол окна — на углу, «пол» — стоит, угол экрана — сидит в углу", () => {
    expect(snap(LIST, 600, 310)?.pose).toBe("sit_edge");
    expect(snap(LIST, 985, 305)?.pose).toBe("perch_corner");
    expect(snap(LIST, 800, 1030)?.pose).toBe("stand");
    expect(snap(LIST, 1910, 1040)?.pose).toBe("sit_corner");
    expect(snap(LIST, 600, 700)).toBeNull(); // посреди окна опоры нет
  });

  it("бок окна: вверху — висит, ниже — стоит у стены, лицом от неё и не заходя в окно", () => {
    const left = snap(LIST, 145, 320);
    expect(left?.pose).toBe("hang_side");
    expect(left?.facing).toBe(-1);
    expect(left?.x).toBeLessThan(200);
    const right = snap(LIST, 1055, 450);
    expect(right?.pose).toBe("lean_side");
    expect(right?.facing).toBe(1);
    expect(right?.x).toBeGreaterThan(1000);
  });

  it("под точкой — ближайший край ниже, иначе «пол»", () => {
    expect(below(LIST, 600, 100)?.y).toBe(300);
    expect(below(LIST, 100, 100)?.y).toBe(1040);
  });

  it("активное окно — правая треть края; рабочий стол — «пол», развёрнутое — угол", () => {
    const seat = seatSpot(LIST, 1, 200, 800);
    expect(seat?.x).toBe(800);
    expect(followSpot(WORLD, LIST, { kind: "desktop" })?.pose).toBe("stand");
    expect(followSpot(WORLD, LIST, { kind: "maximized", app: "chrome" })?.pose).toBe("sit_corner");
    expect(floorSpot(LIST, true)?.x).toBe(1900);
  });

  it("физические пиксели при масштабе 150% → CSS", () => {
    const css = worldToCss({ ...WORLD, monitor: { x: 0, y: 0, w: 2880, h: 1620 } }, 1.5);
    expect(css.seats[0]?.rect).toEqual({ x: 200 / 1.5, y: 200, w: 800 / 1.5, h: 500 / 1.5 });
  });
});

describe("поведение", () => {
  function seated(): Brain {
    const brain = new Brain(() => 0.5);
    brain.setWorld(WORLD);
    const spot = snap(LIST, 600, 300);
    if (spot === null) throw new Error("нет места");
    brain.place(spot);
    return brain;
  }

  it("близко — пешком, далеко — молнией", () => {
    const brain = seated();
    const near = snap(LIST, 800, 300);
    if (near === null) throw new Error("нет места");
    brain.goTo(near);
    expect(brain.phase).toBe("walk");
    settle(brain);
    expect([brain.phase, brain.x]).toEqual(["rest", 800]);

    const far = seatSpot(LIST, 2, 1200, 500);
    if (far === null) throw new Error("нет места");
    expect(Math.hypot(far.x - brain.x, far.y - brain.y)).toBeGreaterThan(WALK_LIMIT);
    brain.goTo(far);
    expect(brain.phase).toBe("bolt");
    expect(brain.body().effects.map((e) => e.kind)).toContain("bolt");
    settle(brain, 1);
    expect([brain.phase, brain.x, brain.y]).toEqual(["rest", far.x, 200]);
  });

  it("окно сдвинули — едет вместе с ним; окно закрыли — падает на «пол»", () => {
    const brain = seated();
    brain.hostMoved(1, { x: 300, y: 350, w: 800, h: 500 });
    expect([brain.x, brain.y]).toEqual([700, 350]);
    brain.setWorld({ ...WORLD, seats: WORLD.seats.slice(1) });
    expect(brain.phase).toBe("fall");
    settle(brain, 4);
    expect([brain.phase, brain.y, brain.body().pose]).toEqual(["rest", 1040, "stand"]);
  });

  it("бросок: отскакивает от стены и пола и в итоге встаёт", () => {
    const brain = seated();
    brain.hold(500, 100);
    expect(brain.body().pose).toBe("held");
    brain.toss(-3000, -500);
    settle(brain, 6);
    expect(brain.phase).toBe("rest");
    expect(brain.x).toBeGreaterThanOrEqual(30);
  });

  it("портал: выходит из точки и уходит обратно", () => {
    const brain = new Brain();
    brain.setWorld(WORLD);
    brain.portalOut(900, 500);
    expect(brain.body().scale).toBe(0);
    settle(brain, 4);
    expect(brain.phase).toBe("rest");
    brain.portalIn();
    settle(brain, 1);
    expect(brain.phase).toBe("hidden");
  });

  it("долгий простой — лежит, потом спит; зов будит", () => {
    const brain = seated();
    settle(brain, 95);
    expect(brain.body().pose).toBe("laydown");
    brain.wake();
    brain.tick(0.016);
    expect(brain.body().pose).toBe("sit_edge");
  });
});

describe("мышь и облачко", () => {
  it("Ctrl — повиснуть, Shift — сесть рядом, иначе — бросок", () => {
    const p = { x: 600, y: 290, shift: false, ctrl: false };
    expect(release(LIST, { ...p, ctrl: true }, { vx: 0, vy: 0 }).kind).toBe("hang");
    expect(release(LIST, { ...p, shift: true }, { vx: 0, vy: 0 }).kind).toBe("place");
    // Спокойно у края окна — закрепиться; резко — бросок; вдали от опор — бросок.
    const calm = release(LIST, p, { vx: 500, vy: 0 });
    expect(calm.kind === "place" && calm.spot.pose).toBe("sit_edge");
    expect(release(LIST, p, { vx: 2000, vy: 0 })).toEqual({ kind: "toss", vx: 2000, vy: 0 });
    expect(release(LIST, { ...p, y: 600 }, { vx: 0, vy: 0 })).toEqual({
      kind: "toss",
      vx: 0,
      vy: 0,
    });
    // Верхний угол экрана и бок окна — тоже места, куда закрепиться.
    const corner = release(LIST, { ...p, x: 20, y: 30 }, { vx: 0, vy: 0 });
    expect(corner.kind === "place" && corner.spot.pose).toBe("hang_side");
    const side = release(LIST, { ...p, x: 1050, y: 450 }, { vx: 0, vy: 0 });
    expect(side.kind === "place" && side.spot.pose).toBe("lean_side");
  });

  it("скорость по следу за 80 мс", () => {
    const trail = [
      { x: 0, y: 0, t: 0 },
      { x: 100, y: 0, t: 100 },
      { x: 150, y: 20, t: 150 },
    ];
    expect(velocityOf(trail)).toEqual({ vx: 1000, vy: 400 });
    expect(velocityOf([])).toEqual({ vx: 0, vy: 0 });
  });

  it("облачко — хвост реплики целыми словами", () => {
    expect(bubbleText("коротко")).toBe("коротко");
    const long = bubbleText("слово ".repeat(60));
    expect(long.startsWith("…слово")).toBe(true);
    expect(long.length).toBeLessThanOrEqual(141);
  });
});

describe("молния, позы, настройки", () => {
  it("молния начинается и кончается в заданных точках, разряд бежит по ней", () => {
    const points = lightning([0, 0], [400, 0], seeded(7));
    expect(points[0]).toEqual([0, 0]);
    expect(points.at(-1)).toEqual([400, 0]);
    expect(points.length).toBe(65);
    expect(along(points, 0)).toEqual([0, 0]);
    const [ex, ey] = along(points, 1);
    expect(ex).toBeCloseTo(400);
    expect(ey).toBeCloseTo(0);
    expect(lightning([0, 0], [400, 0], seeded(7))).toEqual(points);
  });

  it("кадр: речь по громкости, моргание, цикл позы, замены", () => {
    const quiet = { time: 0, mouth: 0, speaking: false, blink: null };
    const have = new Set([
      "stand",
      "sit_edge",
      "sit_edge_talk",
      "sit_edge_blink",
      "sit_edge_blink_1",
    ]);
    expect(pickFrame("sit_edge", { ...quiet, speaking: true, mouth: 0.6 }, have)).toBe(
      "sit_edge_talk",
    );
    expect(pickFrame("sit_edge", { ...quiet, blink: 0.5 }, have)).toBe("sit_edge_blink");
    expect(pickFrame("sit_edge", { ...quiet, blink: 0.1 }, have)).toBe("sit_edge_blink_1");
    expect(pickFrame("perch_corner", quiet, have)).toBe("sit_edge");
    expect(pickFrame("held", quiet, have)).toBe("stand");
    expect(pickFrame("held", quiet, new Set())).toBeNull();

    const walk = new Set(["stand", "walk_1", "walk_2", "walk_3", "walk_4"]);
    expect(sequence("walk", walk)).toEqual(["walk_1", "walk_2", "walk_3", "walk_4"]);
    expect(pickFrame("walk", { ...quiet, time: 0 }, walk)).toBe("walk_1");
    expect(pickFrame("walk", { ...quiet, time: 0.25 }, walk)).toBe("walk_3"); // 10 кадров/с

    const talk = new Set(["stand", "stand_talk_1", "stand_talk_2", "stand_talk_3"]);
    expect(pickFrame("stand", { ...quiet, speaking: true, mouth: 0.1 }, talk)).toBe("stand_talk_1");
    expect(pickFrame("stand", { ...quiet, speaking: true, mouth: 0.95 }, talk)).toBe(
      "stand_talk_3",
    );
    expect(pickFrame("sleep", quiet, new Set(["laydown", "laydown_blink"]))).toBe("laydown_blink");
    expect(poseName("Sit_Edge.PNG")).toBe("sit_edge");
    expect(poseName("walk_3.png")).toBe("walk_3");
    expect(poseName("stand_talk_2.webp")).toBe("stand_talk_2");
    expect(poseName("notes.txt")).toBeNull();
  });

  it("настройки: битое — умолчания; полный экран прячет всегда", () => {
    expect(parseSettings("{oops")).toEqual(DEFAULT_SETTINGS);
    expect(parseSettings('{"when":"always","height":9999}').height).toBe(280);
    const always = { ...DEFAULT_SETTINGS, when: "always" as const };
    expect(shouldShow(DEFAULT_SETTINGS, true)).toBe(false);
    expect(shouldShow(DEFAULT_SETTINGS, false)).toBe(true);
    expect(shouldShow(always, true)).toBe(true);
    expect(shouldShow({ ...always, when: "off" }, false)).toBe(false);
  });
});

describe("инициатива и новые опоры", () => {
  it("верхние углы и верх экрана — висит; бока экрана — облокотился", () => {
    expect(snap(LIST, 10, 8)?.pose).toBe("hang_side");
    expect(snap(LIST, 1910, 5)?.pose).toBe("hang_side");
    expect(snap(LIST, 960, 3)?.pose).toBe("hang_side");
    expect(snap(LIST, 50, 700)?.pose).toBe("lean_side");
  });

  it("сам прогуливается в «следовать»", () => {
    const rolls = [0.1, 0.9, 0.3, 0.7];
    let i = 0;
    const brain = new Brain(() => rolls[i++ % rolls.length] ?? 0.5);
    brain.setWorld(WORLD);
    const floor = snap(LIST, 800, 1040);
    if (floor === null) throw new Error("нет места");
    brain.place(floor);
    brain.wander = true;
    brain.calm = true;
    let walked = false;
    for (let t = 0; t < 60; t += 0.05) {
      brain.tick(0.05);
      if (brain.phase === "walk") walked = true;
    }
    expect(walked).toBe(true);
  });

  it("тема по программе и комментарий без повтора подряд", () => {
    const t = messagesFor("ru");
    expect(topicOf("chrome", false)).toBe("browser");
    expect(topicOf("code", false)).toBe("code");
    expect(topicOf("неизвестно", false)).toBe("other");
    expect(topicOf("", true)).toBe("desktop");
    const first = remark(t, { topic: "code", hour: 14, idleS: 0 }, () => 0.1);
    expect(t.companion.remarks.code).toContain(first);
    const second = remark(t, { topic: "code", hour: 14, idleS: 0 }, () => 0.1, first);
    expect(second).not.toBe(first);
    expect(t.companion.remarks.night).toContain(
      remark(t, { topic: "code", hour: 2, idleS: 0 }, () => 0.9),
    );
  });

  it("тыкает в элемент: палец к ближнему краю, тело — где есть место; подлетел и вернулся", () => {
    const screen = { x: 0, y: 0, w: 1920, h: 1040 };
    const button = { name: "Корзина", kind: "item", rect: { x: 10, y: 100, w: 70, h: 60 } };
    const far = { name: "OK", kind: "button", rect: { x: 900, y: 500, w: 80, h: 30 } };
    expect(choosePoke([button], screen, () => 0)).toEqual({
      x: 80,
      y: 130,
      facing: -1,
      name: "Корзина",
    });
    expect(choosePoke([far], screen, () => 0)).toEqual({ x: 900, y: 515, facing: 1, name: "OK" });
    expect(choosePoke([], screen)).toBeNull();

    const brain = new Brain(() => 0.5);
    brain.setWorld(WORLD);
    const home = snap(LIST, 800, 1040);
    if (home === null) throw new Error("нет места");
    brain.place(home);
    brain.visit(900, 515, "poke", 1);
    settle(brain, 1);
    expect([brain.phase, brain.x, brain.y, brain.body().pose]).toEqual(["rest", 900, 515, "poke"]);
    brain.goTo(home);
    settle(brain, 2);
    expect([brain.phase, brain.body().pose]).toEqual(["rest", "stand"]);
  });
});

describe("взгляд на мышь", () => {
  it("в покое смотрит на курсор с порогом, а занятый своим — нет", () => {
    const brain = new Brain(() => 0.5);
    brain.setWorld(WORLD);
    const floor = snap(LIST, 800, 1040);
    if (floor === null) throw new Error("нет места");
    brain.place(floor);
    brain.cursorX = 100;
    brain.tick(0.016);
    expect(brain.facing).toBe(-1);
    brain.cursorX = 820; // в пределах порога — не дёргается
    brain.tick(0.016);
    expect(brain.facing).toBe(-1);
    brain.cursorX = 1500;
    brain.tick(0.016);
    expect(brain.facing).toBe(1);
    brain.busy = true;
    brain.cursorX = 100;
    brain.tick(0.016);
    expect(brain.facing).toBe(1);
  });
});

describe("поглаживание", () => {
  it("гладят стоящего: поза «довольный», сердечки, потом снова «стоит»", () => {
    const brain = new Brain(() => 0.5);
    brain.setWorld(WORLD);
    const floor = snap(LIST, 800, 1040);
    if (floor === null) throw new Error("нет места");
    brain.place(floor);
    brain.pet();
    const body = brain.body();
    expect(body.pose).toBe("pet");
    expect(body.petting).toBe(1);
    expect(body.effects.map((e) => e.kind)).toContain("hearts");
    settle(brain, 1.5);
    expect([brain.body().pose, brain.body().petting]).toEqual(["stand", 0]);
    // Без кадра «довольный» рисуется «стоит» с закрытыми глазами.
    const have = new Set(["stand", "stand_blink"]);
    expect(pickFrame("pet", { time: 0, mouth: 0, speaking: false, blink: 0.5 }, have)).toBe(
      "stand_blink",
    );
  });
});

describe("значки рабочего стола", () => {
  it("садится на значок, перепрыгивает на другой; значки закрыли — падает на «пол»", () => {
    const brain = new Brain(() => 0.5);
    brain.setWorld({ ...WORLD, seats: [] });
    brain.setIcons([
      { x: 0, y: 20, w: 75, h: 70 },
      { x: 0, y: 300, w: 75, h: 70 },
      { x: 0, y: 390, w: 75, h: 70 },
    ]);
    // У верхнего края на значок не садится: голова ушла бы за экран.
    expect(snap(brain.surfaceList, 37, 26, 30)).toBeNull();
    const first = snap(brain.surfaceList, 37, 306, 50);
    expect(first?.pose).toBe("sit_edge");
    if (first === null) throw new Error("нет значка");
    // Значок у левого края — садится со сдвигом внутрь, чтобы не уйти наполовину за экран.
    expect(first.x).toBeGreaterThanOrEqual(70);
    brain.place(first);
    const second = snap(brain.surfaceList, 37, 396, 50);
    if (second === null) throw new Error("нет значка");
    brain.goTo(second);
    settle(brain, 2);
    expect([brain.phase, brain.y]).toEqual(["rest", 396]);
    brain.setIcons([]);
    settle(brain, 3);
    // Значки у левого края: упав у самого угла экрана, садится в угол.
    expect([brain.phase, brain.y, brain.body().pose]).toEqual(["rest", 1040, "sit_corner"]);
  });
});

describe("placeBubble", () => {
  const view = { w: 1920, h: 1080 };
  const size = { w: 200, h: 50 };

  it("stays inside the screen at the left edge", () => {
    const at = placeBubble({ x: -40, y: 500, w: 160, h: 300 }, size, view);
    expect(at.x).toBeGreaterThanOrEqual(8);
    expect(at.y + size.h).toBeLessThanOrEqual(524);
  });

  it("goes beside the head when there is no room above", () => {
    const at = placeBubble({ x: 1700, y: 0, w: 160, h: 300 }, size, view);
    expect(at.y).toBeGreaterThanOrEqual(8);
    expect(at.x + size.w).toBeLessThanOrEqual(1700);
  });
});
