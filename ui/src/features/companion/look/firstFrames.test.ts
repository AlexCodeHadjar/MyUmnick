import { describe, expect, it } from "vitest";

import { isFirstFrame } from "./pack";

describe("первые кадры при запуске", () => {
  it("позы начала — первыми, переходы и прочие позы — потом", () => {
    expect(isFirstFrame("stand")).toBe(true);
    expect(isFirstFrame("walk_3")).toBe(true);
    expect(isFirstFrame("stand_to_wave_1")).toBe(false);
    expect(isFirstFrame("jukebox_2")).toBe(false);
    expect(isFirstFrame("sit_corner")).toBe(true);
  });
});
