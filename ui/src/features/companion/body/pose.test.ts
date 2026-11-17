import { describe, expect, it } from "vitest";

import { poseOf, type PoseState } from "./pose";

const base: PoseState = {
  pinned: null,
  phase: "rest",
  spot: "stand",
  emote: null,
  watching: false,
  music: "off",
  petting: false,
  idle: 0,
  layAfter: 90,
  sleepAfter: 300,
};

describe("выбор позы", () => {
  it("движение важнее места, закреплённое — важнее всего", () => {
    expect(poseOf({ ...base, phase: "walk" })).toBe("walk");
    expect(poseOf({ ...base, phase: "fall" })).toBe("float");
    expect(poseOf({ ...base, phase: "walk", pinned: "poke" })).toBe("poke");
  });

  it("режимы на месте: видео в углу, радио стоя, гладят", () => {
    expect(poseOf({ ...base, spot: "sit_corner", watching: true })).toBe("watch");
    expect(poseOf({ ...base, music: "playing" })).toBe("jukebox");
    expect(poseOf({ ...base, music: "paused" })).toBe("radio_idle");
    expect(poseOf({ ...base, spot: "sit_edge", music: "playing" })).toBe("sit_edge");
    expect(poseOf({ ...base, petting: true })).toBe("pet");
  });

  it("простой: лёг, потом уснул; эмоция перебивает", () => {
    expect(poseOf({ ...base, idle: 100 })).toBe("laydown");
    expect(poseOf({ ...base, idle: 400 })).toBe("sleep");
    expect(poseOf({ ...base, idle: 400, emote: "yawn" })).toBe("yawn");
  });
});
