import { describe, expect, it } from "vitest";

import { PET_EN } from "./phrases/pet.en";
import { PET_RU } from "./phrases/pet.ru";
import { petLine, petSection, type PetPhrases } from "./phrases";
import { Cooldowns, CursorWatch, dragged, lateNight, shaken } from "./triggers";

const calm = {
  count: 1,
  sleeping: false,
  singing: false,
  shaken: false,
  comeback: false,
  hour: 14,
};

describe("триггеры", () => {
  it("перезарядка: второй раз раньше срока не срабатывает", () => {
    const cool = new Cooldowns();
    expect(cool.ready("drag", 0)).toBe(true);
    expect(cool.ready("drag", 30)).toBe(false);
    expect(cool.ready("drag", 61)).toBe(true);
  });

  it("курсор: возвращение после 10 мин, «смотрит» 4 с рядом, рывок рядом", () => {
    const watch = new CursorWatch();
    const body = { x: 500, y: 500 };
    watch.feed(0, 0, 0, null);
    expect(watch.feed(10, 10, 700, null)).toContain("comeback");
    expect(watch.feed(520, 500, 701, body)).toEqual([]);
    expect(watch.feed(520, 500, 705.5, body)).toContain("stare");
    expect(watch.feed(560, 500, 705.51, body)).toContain("flinch");
  });

  it("долгая работа без перерыва — «разомнись»", () => {
    const watch = new CursorWatch();
    let out: string[] = [];
    for (let t = 0; t <= 3100; t += 30) out = watch.feed(t % 60, 0, t, null);
    expect(out).toContain("stretch");
  });

  it("тряска — три разворота быстрее 1500 px/с за секунду", () => {
    const trail = [0, 1, 2, 3, 4].map((i) => ({ x: i % 2 === 0 ? 0 : 200, y: 0, t: i * 100 }));
    expect(shaken(trail)).toBe(true);
    expect(shaken(trail.map((p) => ({ ...p, x: p.x / 10 })))).toBe(false);
  });

  it("окно тащат быстро, ночь — с часа до пяти", () => {
    expect(dragged({ x: 0, y: 0 }, { x: 100, y: 0 }, 0.1)).toBe(true);
    expect(dragged({ x: 0, y: 0 }, { x: 10, y: 0 }, 0.1)).toBe(false);
    expect([0, 1, 4, 5].map(lateNight)).toEqual([false, true, true, false]);
  });
});

describe("фразы поглаживания", () => {
  it("раздел по клику серии и состоянию; на прочих кликах молчит", () => {
    const never = (): number => 0.9;
    expect(petSection(calm, never)).toBe("first");
    expect(petSection({ ...calm, count: 2 }, never)).toBeNull();
    expect(petSection({ ...calm, count: 3 }, never)).toBe("more");
    expect(petSection({ ...calm, count: 10 }, never)).toBe("overload");
    expect(petSection({ ...calm, count: 15 }, never)).toBe("max");
    expect(petSection({ ...calm, sleeping: true }, never)).toBe("sleepy");
    expect(petSection({ ...calm, shaken: true }, never)).toBe("held");
    expect(petSection({ ...calm, singing: true }, never)).toBe("singing");
    expect(petSection({ ...calm, hour: 2 }, () => 0.1)).toBe("night");
  });

  it("без повтора последних 12", () => {
    const recent: string[] = [];
    const said = new Set<string>();
    let i = 0;
    for (let n = 0; n < 12; n += 1) said.add(petLine(PET_RU.first, recent, () => (i++ % 7) / 7));
    expect(said.size).toBe(12);
  });

  it("большой набор: в каждом разделе есть фразы, у изданий одинаковые разделы и не длиннее облачка", () => {
    expect(Object.keys(PET_EN).sort()).toEqual(Object.keys(PET_RU).sort());
    const sections: (keyof PetPhrases)[] = [
      "first",
      "more",
      "lots",
      "overload",
      "max",
      "sleepy",
      "morning",
      "night",
      "singing",
      "held",
      "comeback",
    ];
    expect([...sections].sort()).toEqual(Object.keys(PET_RU).sort());
    const all: (readonly string[])[] = sections.flatMap((key) => [PET_RU[key], PET_EN[key]]);
    expect(all.every((list) => list.length >= 8)).toBe(true);
    expect(all.flat().every((line) => line.length <= 140)).toBe(true);
    expect(sections.flatMap((key) => PET_RU[key]).length).toBeGreaterThanOrEqual(130);
  });
});
