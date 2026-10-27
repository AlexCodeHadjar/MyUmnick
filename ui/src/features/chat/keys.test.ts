import { describe, expect, it } from "vitest";

import { isSendKey, isStopKey } from "./keys";

const key = (key: string, shiftKey = false, isComposing = false) => ({
  key,
  shiftKey,
  isComposing,
});

describe("клавиши ввода", () => {
  it("Enter отправляет, Shift+Enter — нет", () => {
    expect(isSendKey(key("Enter"))).toBe(true);
    expect(isSendKey(key("Enter", true))).toBe(false);
    expect(isSendKey(key("a"))).toBe(false);
  });

  it("во время набора через IME Enter и Esc не срабатывают", () => {
    expect(isSendKey(key("Enter", false, true))).toBe(false);
    expect(isStopKey(key("Escape", false, true))).toBe(false);
  });

  it("Esc останавливает ответ", () => {
    expect(isStopKey(key("Escape"))).toBe(true);
    expect(isStopKey(key("Enter"))).toBe(false);
  });
});
