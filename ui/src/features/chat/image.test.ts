import { describe, expect, it } from "vitest";

import { fitSize, MAX_IMAGE_SIDE } from "./image";

describe("размер картинки", () => {
  it("большая вписывается с сохранением пропорций", () => {
    expect(fitSize({ width: 4000, height: 2000 })).toEqual({
      width: MAX_IMAGE_SIDE,
      height: MAX_IMAGE_SIDE / 2,
    });
    expect(fitSize({ width: 1000, height: 4000 }, 400)).toEqual({ width: 100, height: 400 });
  });

  it("маленькая не растягивается", () => {
    expect(fitSize({ width: 200, height: 100 })).toEqual({ width: 200, height: 100 });
  });

  it("нулевой размер не ломает холст", () => {
    expect(fitSize({ width: 0, height: 0 })).toEqual({ width: 1, height: 1 });
  });
});
