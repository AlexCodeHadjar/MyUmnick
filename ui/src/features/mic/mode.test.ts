import { describe, expect, it } from "vitest";

import { isPushToTalk, parseMode } from "./mode";

describe("режим микрофона", () => {
  it("неизвестное значение — выключен", () => {
    expect(parseMode("always")).toBe("always");
    expect(parseMode("push")).toBe("push");
    expect(parseMode("boom")).toBe("off");
    expect(parseMode(null)).toBe("off");
  });

  it("клавиша — по коду, работает в любой раскладке", () => {
    expect(isPushToTalk({ code: "F9" })).toBe(true);
    expect(isPushToTalk({ code: "F8" })).toBe(false);
  });
});
