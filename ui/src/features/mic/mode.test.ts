import { describe, expect, it } from "vitest";

import { isPushToTalk, parseMode, startMode } from "./mode";

describe("режим микрофона", () => {
  it("в фоне слушает всегда, иначе — сохранённый выбор", () => {
    expect(startMode("off", true)).toBe("always");
    expect(startMode("push", true)).toBe("always");
    expect(startMode("push", false)).toBe("push");
  });

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
