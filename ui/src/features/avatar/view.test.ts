import { describe, expect, it } from "vitest";

import { DEFAULT_VIEW, parseView } from "./view";

describe("вид показа", () => {
  it("неизвестное или старое значение (модель Live2D) — вид по умолчанию", () => {
    expect(parseView("orb")).toBe("orb");
    expect(parseView("portrait")).toBe("portrait");
    expect(DEFAULT_VIEW).toBe("portrait");
    expect(parseView("haru")).toBe(DEFAULT_VIEW);
    expect(parseView(null)).toBe(DEFAULT_VIEW);
  });
});
