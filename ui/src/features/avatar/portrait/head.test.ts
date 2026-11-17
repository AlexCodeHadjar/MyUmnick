import { describe, expect, it } from "vitest";

import { headFrame } from "./head";

const calm = { speaking: false, mouth: 0, blink: null, emotion: "neutral", intensity: 0 } as const;
const name = (url: string): string => url.slice(url.lastIndexOf("/") + 1, -5);

describe("мордашка", () => {
  it("рот по громкости в три уровня", () => {
    expect(name(headFrame({ ...calm, speaking: true, mouth: 0.1 }))).toBe("head_talk_1");
    expect(name(headFrame({ ...calm, speaking: true, mouth: 0.5 }))).toBe("head_talk_2");
    expect(name(headFrame({ ...calm, speaking: true, mouth: 1 }))).toBe("head_talk_3");
  });

  it("моргание: полуприкрытые глаза по краям, закрытые в середине", () => {
    expect(name(headFrame({ ...calm, blink: 0.1 }))).toBe("head_blink_1");
    expect(name(headFrame({ ...calm, blink: 0.5 }))).toBe("head_blink");
  });

  it("лицо по эмоции, слабая эмоция и «нейтрально» — обычное", () => {
    expect(name(headFrame({ ...calm, emotion: "sad", intensity: 0.8 }))).toBe("head_sad");
    expect(name(headFrame({ ...calm, emotion: "embarrassed", intensity: 0.8 }))).toBe("head_happy");
    expect(name(headFrame({ ...calm, emotion: "sad", intensity: 0.1 }))).toBe("head");
    expect(name(headFrame(calm))).toBe("head");
  });
});
