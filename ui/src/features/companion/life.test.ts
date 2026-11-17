import { describe, expect, it } from "vitest";

import { AppWatch, isRecycleBin, parseFavorites, pickIcon } from "./habits";
import { drift, neutralMood, nudge, pace, parseMood, restTimes, tone } from "./mood";
import { browserTopic, siteOf } from "./sites";

describe("настроение", () => {
  it("поглаживания радуют, тряска огорчает, всё в пределах 0…1", () => {
    let mood = neutralMood(0);
    for (let i = 0; i < 30; i += 1) mood = nudge(mood, "pet");
    expect(mood.joy).toBe(1);
    expect(tone(mood)).toBe("high");
    for (let i = 0; i < 10; i += 1) mood = nudge(mood, "shake");
    expect(mood.joy).toBe(0);
    expect(tone(mood)).toBe("low");
  });

  it("ночью устаёт — ложится и засыпает раньше, гуляет реже", () => {
    let mood = neutralMood(0);
    mood = drift(mood, 30 * 60, { hour: 2, idleS: 0 });
    expect(mood.energy).toBeLessThan(0.25);
    expect(restTimes(mood)).toEqual({ lay: 45, sleep: 150 });
    expect(pace(mood)).toBeGreaterThan(pace(neutralMood(0)));
  });

  it("за ночь без запуска — к середине; битое — среднее", () => {
    const saved = JSON.stringify({ energy: 0, joy: 1, at: 0 });
    expect(parseMood(saved, 8 * 3_600_000)).toMatchObject({ energy: 0.6, joy: 0.6 });
    expect(parseMood(saved, 0)).toMatchObject({ energy: 0, joy: 1 });
    expect(parseMood("{", 5)).toEqual(neutralMood(5));
  });
});

describe("сайты браузера", () => {
  it("тема по названию вкладки", () => {
    expect(siteOf("Котики — YouTube")).toBe("video");
    expect(siteOf("AlexCodeHadjar/MyUmnick · GitHub")).toBe("code");
    expect(siteOf("Яндекс Музыка — слушайте")).toBe("music");
    expect(siteOf("Яндекс: нашлось 3 млн")).toBe("search");
    expect(siteOf("Моя страница")).toBeNull();
  });

  it("много вкладок — шутка; ничего не узнал — null", () => {
    const many = Array.from({ length: 25 }, (_, i) => `Вкладка ${String(i)}`);
    expect(browserTopic(many, () => 0.1)).toBe("many");
    expect(browserTopic(["Новая вкладка"], () => 0.5)).toBeNull();
    expect(browserTopic(["Gmail — Входящие", "x"], () => 0.9)).toBe("mail");
  });
});

describe("привычки", () => {
  it("первый раз за день, долго в одной программе, частые переключения", () => {
    const watch = new AppWatch();
    expect(watch.focus("code", 0, "2026-11-17")).toEqual(["first"]);
    expect(watch.focus("browser", 10, "2026-11-17")).toEqual(["first"]);
    expect(watch.focus("code", 20, "2026-11-17")).toEqual([]);
    expect(watch.tick(20 + 39 * 60)).toBeNull();
    expect(watch.tick(20 + 41 * 60)).toBe("long");
    expect(watch.tick(20 + 50 * 60)).toBeNull();
    expect(watch.focus("code", 0, "2026-11-18")).toEqual([]);
    let out: string[] = [];
    for (let i = 0; i < 9; i += 1)
      out = watch.focus(i % 2 === 0 ? "chat" : "files", 100 + i, "2026-11-18");
    expect(out).toContain("switching");
  });

  it("любимый значок выбирается чаще; корзина узнаётся", () => {
    const icons = [{ name: "Steam" }, { name: "Корзина" }];
    const favorites = parseFavorites(JSON.stringify({ Steam: 20, bad: "x" }));
    expect(favorites.size).toBe(1);
    expect(pickIcon(icons, favorites, () => 0.9)?.name).toBe("Steam");
    expect(pickIcon(icons, new Map(), () => 0.9)?.name).toBe("Корзина");
    expect(["Корзина", "Recycle Bin", "Steam"].map(isRecycleBin)).toEqual([true, true, false]);
  });
});
