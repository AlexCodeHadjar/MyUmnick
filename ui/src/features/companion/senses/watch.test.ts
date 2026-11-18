import { describe, expect, it } from "vitest";

import { floorSpot, surfaces } from "../space";
import { Brain } from "../body";
import { pickFrame } from "../look";
import { watchPhrases } from "../phrases";
import { keepWatching, loudMoment, mediaVideo, musicPlaying, pickMedia, watching } from "./watch";
import type { World } from "../space";

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

describe("кадры пения", () => {
  it("поёт спокойно: только медленный цикл, кадры рта не вклиниваются даже на громких местах", () => {
    const have = new Set(["stand", "sing", "sing_1", "sing_2", "sing_talk_1", "sing_talk_3"]);
    const state = { time: 0, mouth: 0.95, speaking: true, blink: null };
    expect(pickFrame("sing", state, have)).toBe("sing_1");
    // Ящика ещё нет — замена: тот же спокойный цикл пения.
    expect(pickFrame("jukebox", state, have)).toBe("sing_1");
    expect(pickFrame("jukebox", state, new Set([...have, "jukebox", "jukebox_1"]))).toBe(
      "jukebox_1",
    );
    expect(
      pickFrame("radio_idle", { ...state, mouth: 0.5 }, new Set(["stand", "stand_talk_1"])),
    ).toBe("stand_talk_1");
  });
});

describe("что играет в системе", () => {
  const base = { pausedS: 0, tab: null, focusVideo: false, already: false };

  it("браузер или плеер — видео, музыкальная программа или вкладка — нет", () => {
    expect(mediaVideo({ state: "playing", app: "chrome.exe" }, null)).toBe(true);
    expect(mediaVideo({ state: "playing", app: "vlc.exe" }, null)).toBe(true);
    expect(mediaVideo({ state: "playing", app: "spotify.exe" }, null)).toBe(false);
    expect(mediaVideo({ state: "playing", app: "msedge" }, "Яндекс Музыка — плейлист")).toBe(false);
    expect(mediaVideo({ state: "none", app: "" }, null)).toBe(false);
  });

  it("начинает, только если видео в фокусе; уже смотрим — держится, пока фильм идёт", () => {
    const playing = { state: "playing" as const, app: "chrome.exe" };
    expect(keepWatching({ ...base, media: playing })).toBe(false);
    expect(keepWatching({ ...base, media: playing, focusVideo: true })).toBe(true);
    expect(keepWatching({ ...base, media: playing, already: true })).toBe(true);
    const paused = { state: "paused" as const, app: "chrome.exe" };
    expect(keepWatching({ ...base, media: paused, already: true, pausedS: 30 })).toBe(true);
    expect(keepWatching({ ...base, media: paused, already: true, pausedS: 120 })).toBe(false);
  });

  it("фразы просмотра: большой универсальный набор на обоих языках", () => {
    for (const lang of ["ru", "en"]) {
      const lines = watchPhrases(lang);
      expect(lines.during.length).toBeGreaterThanOrEqual(50);
      expect(
        [lines.start, lines.pause, lines.resume, lines.end].every((one) => one.length >= 6),
      ).toBe(true);
    }
  });
});

describe("выбор источника", () => {
  it("видео — браузер, а не встроенный веб-движок или мессенджер; играющее важнее паузы", () => {
    const list = [
      { state: "playing" as const, app: "msedgewebview2" },
      { state: "paused" as const, app: "telegram" },
      { state: "paused" as const, app: "browser" },
    ];
    expect(pickMedia(list, null)).toEqual({ state: "paused", app: "browser" });
    expect(pickMedia([...list, { state: "playing" as const, app: "vlc" }], null).app).toBe("vlc");
    expect(pickMedia([{ state: "playing" as const, app: "msedgewebview2" }], null).state).toBe(
      "none",
    );
  });
});

describe("музыка в плеере", () => {
  it("играет музыкальная программа — да; браузер или пауза — нет", () => {
    expect(musicPlaying([{ state: "playing", app: "spotify.exe" }])).toBe(true);
    expect(musicPlaying([{ state: "paused", app: "spotify.exe" }])).toBe(false);
    expect(musicPlaying([{ state: "playing", app: "chrome.exe" }])).toBe(false);
  });
});

describe("громкие места", () => {
  it("пик заметно выше обычного — громкое место; ровно громко — нет", () => {
    expect(loudMoment(0.95, 0.3)).toBe(true);
    expect(loudMoment(0.8, 0.7)).toBe(false);
    expect(loudMoment(0.5, 0.1)).toBe(false);
  });
});
