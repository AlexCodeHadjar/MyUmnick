import { describe, expect, it } from "vitest";

import { ClickThrough } from "./clickThrough";
import { isDesktopHotkey, loadDesktop, saveDesktop, type DesktopStorage, type Point } from "./mode";

function memoryStorage(initial?: string): DesktopStorage {
  const items = new Map<string, string>();
  if (initial !== undefined) {
    items.set("vtuber.desktop", initial);
  }
  return {
    getItem: (key) => items.get(key) ?? null,
    setItem: (key, value) => {
      items.set(key, value);
    },
  };
}

describe("запоминание режима", () => {
  it("режим переживает перезапуск", () => {
    const storage = memoryStorage();
    saveDesktop(storage, { overlay: true, pinned: false });
    expect(loadDesktop(storage)).toEqual({ overlay: true, pinned: false });
  });

  it("без записи — обычное окно, закрепление по умолчанию включено", () => {
    expect(loadDesktop(memoryStorage())).toEqual({ overlay: false, pinned: true });
    expect(loadDesktop(undefined)).toEqual({ overlay: false, pinned: true });
  });

  it.each(["не json", "null", "[]", '{"overlay":"да"}'])(
    "битая запись %s — обычное окно",
    (raw) => {
      expect(loadDesktop(memoryStorage(raw)).overlay).toBe(false);
    },
  );
});

function through(solid: (point: Point) => boolean, failing = false) {
  const calls: boolean[] = [];
  const position = { current: { x: 0, y: 0 } };
  const click = new ClickThrough(
    {
      cursor: () =>
        failing ? Promise.reject(new Error("нет окна")) : Promise.resolve(position.current),
      passClicks: (pass) => {
        calls.push(pass);
        return Promise.resolve();
      },
    },
    solid,
  );
  return { click, calls, position };
}

describe("клики сквозь пустые области", () => {
  const overModel = (point: Point) => point.x > 100;

  it("окно переключается только когда курсор переходит границу", async () => {
    const { click, calls, position } = through(overModel);
    await click.tick();
    await click.tick();
    expect(calls).toEqual([true]);
    position.current = { x: 200, y: 0 };
    await click.tick();
    await click.tick();
    expect(calls).toEqual([true, false]);
  });

  it("выход из режима возвращает клики окну", async () => {
    const { click, calls } = through(overModel);
    await click.tick();
    await click.stop();
    expect(calls).toEqual([true, false]);
  });

  it("окно не ответило — состояние прежнее", async () => {
    const { click, calls } = through(overModel, true);
    await expect(click.tick()).rejects.toThrow("нет окна");
    expect(calls).toEqual([]);
  });
});

describe("хоткей", () => {
  it("только Ctrl+Shift+O", () => {
    const key = { code: "KeyO", ctrlKey: true, shiftKey: true, altKey: false };
    expect(isDesktopHotkey(key)).toBe(true);
    expect(isDesktopHotkey({ ...key, shiftKey: false })).toBe(false);
    expect(isDesktopHotkey({ ...key, altKey: true })).toBe(false);
  });
});
