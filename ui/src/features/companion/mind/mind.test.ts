import { describe, expect, it } from "vitest";

import { Arbiter, type Activity } from "./arbiter";
import { Fact } from "./fact";
import { Mind, type Senses } from "./index";
import { Voice } from "./voice";

const calm: Senses = {
  resting: true,
  listening: false,
  singing: false,
  video: false,
  fullscreen: false,
  desktop: false,
  behavior: "follow",
  energy: 0.6,
  userBusy: false,
  hour: 14,
  calm: false,
};

function activity(
  id: string,
  band: 0 | 1 | 2 | 3,
  score: (c: { a: number }) => number,
): Activity<{ a: number }> {
  return { id, band, minS: 3, cooldownS: 0, boredom: 0, oneShot: false, score };
}

describe("арбитр", () => {
  it("почти равные оценки не дают метаний (инерция и порог)", () => {
    const arbiter = new Arbiter(
      [
        activity("idle", 0, () => 0.1),
        activity("a", 1, (c) => 0.5 + c.a),
        activity("b", 1, (c) => 0.5 - c.a),
      ],
      () => 0.5,
    );
    let switches = 0;
    for (let t = 0; t < 120; t += 0.5) {
      const wobble = Math.sin(t * 3) * 0.04;
      if (arbiter.choose({ a: wobble }, t).changed) switches += 1;
    }
    expect(switches).toBeLessThanOrEqual(1);
  });

  it("важная группа прерывает сразу, менее важная ждёт минимум", () => {
    const arbiter = new Arbiter(
      [
        activity("idle", 0, () => 0.2),
        activity("walk", 1, (c) => (c.a > 0 ? 0.6 : 0)),
        activity("listen", 3, (c) => (c.a > 1 ? 1 : 0)),
      ],
      () => 0.5,
    );
    expect(arbiter.choose({ a: 0.5 }, 0).id).toBe("walk");
    expect(arbiter.choose({ a: 2 }, 0.5).id).toBe("listen");
  });

  it("пауза «осмотреться» откладывает выходки", () => {
    const arbiter = new Arbiter(
      [activity("idle", 0, () => 0.2), activity("walk", 1, () => 0.8)],
      () => 0.5,
    );
    arbiter.settle(0, 3);
    expect(arbiter.choose({ a: 0 }, 1).id).toBe("idle");
    expect(arbiter.choose({ a: 0 }, 3.5).id).toBe("walk");
  });
});

describe("сглаженный факт", () => {
  it("мимолётный сигнал не меняет факт", () => {
    const video = new Fact(2, 4);
    video.update(true, 0);
    expect(video.update(false, 1)).toBe(false);
    video.update(true, 2);
    expect(video.update(true, 4.1)).toBe(true);
    expect(video.update(false, 5)).toBe(true);
    expect(video.update(false, 9.1)).toBe(false);
  });
});

describe("голос", () => {
  it("«сам по себе» — не больше нормы за 10 минут; прямые ответы — сразу", () => {
    const voice = new Voice();
    let said = 0;
    for (let t = 0; t < 600; t += 1) {
      voice.offer(`фраза ${String(t)}`, "ambient", t);
      if (voice.next(t, { blocked: false, bubble: false }) !== null) said += 1;
    }
    expect(said).toBeLessThanOrEqual(9);
    voice.offer("Ой, приятно!", "direct", 600);
    expect(voice.next(600, { blocked: false, bubble: true })).toBe("Ой, приятно!");
  });

  it("пока говорит ассистент — молчит; устаревшая реакция выбрасывается", () => {
    const voice = new Voice();
    voice.offer("Эй, полегче!", "reaction", 0);
    expect(voice.next(1, { blocked: true, bubble: false })).toBeNull();
    expect(voice.next(7, { blocked: false, bubble: false })).toBeNull();
  });
});

describe("разум целиком", () => {
  it("видео на секунду — не садится смотреть; видео 3 с — садится и сидит", () => {
    const mind = new Mind(() => 0.5);
    let t = 0;
    const run = (seconds: number, senses: Senses): void => {
      for (const end = t + seconds; t < end; t += 0.1) mind.update(t, senses);
    };
    run(5, calm);
    run(1, { ...calm, video: true });
    run(1, calm);
    expect(mind.activity).not.toBe("watch");
    run(3, { ...calm, video: true });
    expect(mind.activity).toBe("watch");
    run(2, { ...calm, video: false });
    expect(mind.activity).toBe("watch");
  });

  it("за час покоя — разные выходки, но без суеты", () => {
    const mind = new Mind(() => 0.5);
    const seen = new Map<string, number>();
    for (let t = 0; t < 3600; t += 0.1) {
      const choice = mind.update(t, calm);
      if (choice !== null) seen.set(choice.id, (seen.get(choice.id) ?? 0) + 1);
    }
    const busy = [...seen.entries()].filter(([id]) => id !== "idle");
    const total = busy.reduce((sum, [, n]) => sum + n, 0);
    expect(busy.length).toBeGreaterThanOrEqual(2);
    expect(total).toBeLessThan(120);
    expect(total).toBeGreaterThan(10);
  });
});

describe("спокойный режим", () => {
  it("спокойнее — втрое меньше выходок и ни одного тычка", () => {
    const count = (calmMode: boolean): { total: number; pokes: number } => {
      const mind = new Mind(() => 0.5);
      let total = 0;
      let pokes = 0;
      for (let t = 0; t < 3600; t += 0.1) {
        const choice = mind.update(t, { ...calm, calm: calmMode });
        if (choice === null || choice.id === "idle") continue;
        total += 1;
        if (choice.id === "poke" || choice.id === "hop") pokes += 1;
      }
      return { total, pokes };
    };
    const normal = count(false);
    const quiet = count(true);
    expect(quiet.pokes).toBe(0);
    expect(quiet.total * 2).toBeLessThan(normal.total);
  });
});
