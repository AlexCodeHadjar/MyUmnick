import { describe, expect, it } from "vitest";

import { Mood } from "./mood";

const cfg = { holdMs: 1000, fadeMs: 500 };

describe("Mood", () => {
  it("пока разговор идёт — эмоция в полную силу", () => {
    const mood = new Mood(cfg);
    mood.set("happy");
    for (let i = 0; i < 100; i++) {
      expect(mood.update(100, true)).toEqual({ emotion: "happy", intensity: 1 });
    }
  });

  it("после речи держится holdMs, затем спадает за fadeMs до нейтральной", () => {
    const mood = new Mood(cfg);
    mood.set("sad");
    expect(mood.update(1000, false)).toEqual({ emotion: "sad", intensity: 1 });
    expect(mood.update(250, false).intensity).toBeCloseTo(0.5);
    expect(mood.update(250, false)).toEqual({ emotion: "neutral", intensity: 0 });
  });

  it("новая речь возвращает эмоцию ответа в полную силу", () => {
    const mood = new Mood(cfg);
    mood.set("angry");
    mood.update(5000, false);
    expect(mood.update(16, true)).toEqual({ emotion: "angry", intensity: 1 });
  });

  it("новая эмоция начинает отсчёт заново", () => {
    const mood = new Mood(cfg);
    mood.set("happy");
    mood.update(1400, false);
    mood.set("surprised");
    expect(mood.update(16, false)).toEqual({ emotion: "surprised", intensity: 1 });
  });
});
