import { describe, expect, it } from "vitest";

import { int16ToFloat, StreamResampler } from "./resample";

const ramp = (from: number, length: number): Float32Array =>
  Float32Array.from({ length }, (_, i) => from + i);

describe("int16ToFloat", () => {
  it("s16 → [-1, 1)", () => {
    expect(Array.from(int16ToFloat(Int16Array.from([-32768, 0, 16384])))).toEqual([-1, 0, 0.5]);
  });
});

describe("StreamResampler", () => {
  it("равные частоты — вход как есть", () => {
    const input = ramp(0, 4);
    expect(new StreamResampler(48000, 48000).process(input)).toBe(input);
  });

  it("длина выхода — по отношению частот", () => {
    const resampler = new StreamResampler(24000, 48000);
    let total = 0;
    for (let i = 0; i < 10; i++) {
      total += resampler.process(ramp(0, 480)).length;
    }
    expect(Math.abs(total - 9600)).toBeLessThanOrEqual(2);
  });

  it("поток, нарезанный кусками, совпадает с цельным: стык без щелчка", () => {
    const whole = new StreamResampler(22050, 48000).process(ramp(0, 300));
    const stream = new StreamResampler(22050, 48000);
    const joined = [ramp(0, 7), ramp(7, 1), ramp(8, 150), ramp(158, 142)].flatMap((part) =>
      Array.from(stream.process(part)),
    );
    expect(joined).toHaveLength(whole.length);
    joined.forEach((value, i) => {
      expect(value).toBeCloseTo(whole[i] ?? Number.NaN, 3);
    });
  });

  it("линейная рампа остаётся рампой с шагом fromRate / toRate", () => {
    const out = Array.from(new StreamResampler(48000, 96000).process(ramp(0, 5)));
    expect(out).toEqual([0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5]);
  });

  it("reset — новый ход без стыка с прошлым", () => {
    const resampler = new StreamResampler(48000, 96000);
    resampler.process(ramp(100, 3));
    resampler.reset();
    expect(Array.from(resampler.process(ramp(0, 2)))).toEqual([0, 0.5]);
  });
});
