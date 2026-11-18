import { describe, expect, it } from "vitest";

import { wasOverlay } from "./restoreWindow";

describe("старая запись «поверх стола»", () => {
  it("включённый режим узнаётся", () => {
    expect(wasOverlay('{"overlay":true,"pinned":true}')).toBe(true);
  });

  it("выключенный, испорченный и пустой — нет", () => {
    expect(wasOverlay('{"overlay":false}')).toBe(false);
    expect(wasOverlay("{oops")).toBe(false);
    expect(wasOverlay(null)).toBe(false);
  });
});
