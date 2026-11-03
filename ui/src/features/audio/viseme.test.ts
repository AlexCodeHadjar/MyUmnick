import { describe, expect, it } from "vitest";

import { FormFollower, mouthShape, NEUTRAL_SHAPE } from "./viseme";

const SAMPLE_RATE = 48_000;
const FFT_SIZE = 1024;
const BIN_HZ = SAMPLE_RATE / FFT_SIZE;

/** Как считает AnalyserNode: окно Блэкмана, затем дБ. Частоты выводятся из синусов. */
function spectrum(...tones: [number, number][]): Float32Array {
  const samples = Array.from({ length: FFT_SIZE }, (_, n) => {
    const t = n / SAMPLE_RATE;
    const window =
      0.42 -
      0.5 * Math.cos((2 * Math.PI * n) / FFT_SIZE) +
      0.08 * Math.cos((4 * Math.PI * n) / FFT_SIZE);
    const signal = tones.reduce((sum, [hz, a]) => sum + a * Math.sin(2 * Math.PI * hz * t), 0);
    return window * signal;
  });
  const result = new Float32Array(FFT_SIZE / 2);
  for (let bin = 0; bin < result.length; bin++) {
    let re = 0;
    let im = 0;
    samples.forEach((sample, n) => {
      re += sample * Math.cos((2 * Math.PI * bin * n) / FFT_SIZE);
      im -= sample * Math.sin((2 * Math.PI * bin * n) / FFT_SIZE);
    });
    result[bin] = 20 * Math.log10(Math.hypot(re, im) / FFT_SIZE);
  }
  return result;
}

/** Первая форманта и вторая, тише на 6 дБ: типичные значения русских гласных. */
function vowel(f1: number, f2: number): ReturnType<typeof mouthShape> {
  return mouthShape(spectrum([f1, 0.2], [f2, 0.1]), BIN_HZ);
}

describe("форма рта по спектру", () => {
  const a = vowel(750, 1300);
  const o = vowel(500, 900);
  const u = vowel(320, 700);
  const e = vowel(550, 1900);
  const i = vowel(280, 2300);

  it("«о» и «у» округляют рот, «э» и «и» растягивают, «а» посередине", () => {
    expect(o.form).toBeLessThan(-0.2);
    expect(u.form).toBeLessThan(-0.2);
    expect(e.form).toBeGreaterThan(0.5);
    expect(i.form).toBeGreaterThan(0.5);
    expect(Math.abs(a.form)).toBeLessThan(0.3);
  });

  it("«а» открывает рот шире остальных", () => {
    for (const other of [o, u, e, i]) {
      expect(a.openness).toBeGreaterThan(other.openness);
    }
  });

  it("шипящая почти закрывает рот", () => {
    const hiss = mouthShape(spectrum([5500, 0.3], [6500, 0.3], [300, 0.02]), BIN_HZ);
    expect(hiss.openness).toBeLessThan(0.5);
  });

  it("без данных — откат к громкости", () => {
    expect(mouthShape(new Float32Array(512).fill(-Infinity), BIN_HZ)).toEqual(NEUTRAL_SHAPE);
    expect(mouthShape(new Float32Array(0), BIN_HZ)).toEqual(NEUTRAL_SHAPE);
  });
});

describe("сглаживание формы", () => {
  it("не зависит от частоты кадров", () => {
    const slow = new FormFollower();
    const fast = new FormFollower();
    const once = slow.update(1, 32);
    fast.update(1, 16);
    expect(fast.update(1, 16)).toBeCloseTo(once);
  });

  it("вне речи рот возвращается к нейтральной", () => {
    const follower = new FormFollower();
    follower.update(1, 1000);
    expect(follower.update(null, 1000)).toBeCloseTo(0);
  });
});
