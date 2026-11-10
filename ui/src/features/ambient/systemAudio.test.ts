import { describe, expect, it } from "vitest";

import { shape, SILENCE } from "./systemAudio";

describe("звук компьютера для сферы", () => {
  it("тишина остаётся тишиной", () => {
    expect(shape(SILENCE, SILENCE)).toEqual(SILENCE);
  });

  it("удар баса подхватывается быстро, а спадает плавно", () => {
    const hit = shape({ bass: 0.3, mid: 0, high: 0 }, SILENCE);
    const after = shape(SILENCE, hit);

    expect(hit.bass).toBeGreaterThan(0.3);
    expect(hit.bass).toBeLessThanOrEqual(1);
    expect(after.bass).toBeGreaterThan(hit.bass * 0.8);
  });

  it("громкий звук не уходит за 1", () => {
    let bands = SILENCE;
    for (let i = 0; i < 50; i += 1) bands = shape({ bass: 1, mid: 1, high: 1 }, bands);
    expect(Math.max(bands.bass, bands.mid, bands.high)).toBeLessThanOrEqual(1);
  });
});
