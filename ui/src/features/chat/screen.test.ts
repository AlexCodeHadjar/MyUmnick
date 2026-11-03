import { describe, expect, it, vi } from "vitest";

import type { Attachment } from "./image";
import {
  asksForScreen,
  captureFrom,
  wantsCapture,
  type ScreenSource,
  type Stoppable,
} from "./screen";

const SHOT: Attachment = { image: { mime: "image/jpeg", base64: "QUJD" }, preview: "data:," };

function fakeStream(): { stream: Stoppable; stop: () => void } {
  const stop = vi.fn();
  return { stream: { getTracks: () => [{ stop }] }, stop };
}

function source(stream: Stoppable, frameFails = false): ScreenSource<Stoppable, string> {
  return {
    pick: () => Promise.resolve(stream),
    frame: () =>
      frameFails
        ? Promise.reject(new Error("нет кадра"))
        : Promise.resolve({ source: "кадр", size: { width: 1, height: 1 } }),
  };
}

describe("просьба посмотреть на экран", () => {
  it.each(["Посмотри на экран", "глянь на моё окно", "Что у меня на экране?", "взгляни на экран"])(
    "%s — просьба",
    (text) => {
      expect(asksForScreen(text)).toBe(true);
    },
  );

  it.each(["Как дела?", "У меня сломался экран", "Посмотри кино", "Экран пыльный, окно грязное"])(
    "%s — не просьба",
    (text) => {
      expect(asksForScreen(text)).toBe(false);
    },
  );
});

describe("когда открывать диалог", () => {
  it("только на просьбу и пока ничего не прикреплено", () => {
    expect(wantsCapture("Посмотри на экран", false)).toBe(true);
    expect(wantsCapture("Посмотри на экран", true)).toBe(false);
    expect(wantsCapture("Как дела?", false)).toBe(false);
  });
});

describe("снимок", () => {
  it("один кадр и захват сразу завершён", async () => {
    const { stream, stop } = fakeStream();
    const shot = await captureFrom(source(stream), () => SHOT);
    expect(shot).toBe(SHOT);
    expect(stop).toHaveBeenCalledOnce();
  });

  it("отказ в диалоге — снимка нет и это не ошибка", async () => {
    const refused: ScreenSource<Stoppable, string> = {
      pick: () => Promise.reject(new Error("NotAllowedError")),
      frame: () => Promise.reject(new Error("не должно быть вызвано")),
    };
    await expect(captureFrom(refused, () => SHOT)).resolves.toBeNull();
  });

  it("сбой кадра тоже завершает захват", async () => {
    const { stream, stop } = fakeStream();
    await expect(captureFrom(source(stream, true), () => SHOT)).rejects.toThrow("нет кадра");
    expect(stop).toHaveBeenCalledOnce();
  });
});
