import { describe, expect, it } from "vitest";

import {
  clampRatio,
  DEFAULT_RATIO,
  loadRatio,
  MIN_CHAT_PX,
  MIN_STAGE_PX,
  ratioAt,
  saveRatio,
  type RatioStorage,
} from "./split";

class MemoryStorage implements RatioStorage {
  readonly data = new Map<string, string>();

  getItem(key: string): string | null {
    return this.data.get(key) ?? null;
  }

  setItem(key: string, value: string): void {
    this.data.set(key, value);
  }
}

const broken: RatioStorage = {
  getItem: () => {
    throw new Error("SecurityError");
  },
  setItem: () => {
    throw new Error("QuotaExceededError");
  },
};

describe("clampRatio", () => {
  it("держит обе панели не уже минимума", () => {
    expect(clampRatio(0.05, 1600)).toBe(MIN_CHAT_PX / 1600);
    expect(clampRatio(0.99, 1600)).toBe(1 - MIN_STAGE_PX / 1600);
    expect(clampRatio(0.5, 1600)).toBe(0.5);
  });

  it("окно уже двух минимумов — пропорция минимумов", () => {
    expect(clampRatio(0.9, 500)).toBe(MIN_CHAT_PX / (MIN_CHAT_PX + MIN_STAGE_PX));
  });
});

describe("ratioAt", () => {
  it("доля по указателю; нулевая ширина — умолчание", () => {
    expect(ratioAt(500, 100, 1000)).toBe(0.4);
    expect(ratioAt(10, 0, 0)).toBe(DEFAULT_RATIO);
  });
});

describe("хранение доли", () => {
  it("сохранённое значение читается после «перезапуска»", () => {
    const storage = new MemoryStorage();
    saveRatio(storage, 0.6123456);
    expect(loadRatio(storage)).toBe(0.6123);
  });

  it.each([null, "abc", "0", "1", "-0.3", "NaN"])("битое значение %s — умолчание", (raw) => {
    const storage = new MemoryStorage();
    if (raw !== null) {
      storage.data.set("vtuber.layout.chatRatio", raw);
    }
    expect(loadRatio(storage)).toBe(DEFAULT_RATIO);
  });

  it("недоступное хранилище не ломает раскладку", () => {
    expect(loadRatio(broken)).toBe(DEFAULT_RATIO);
    expect(() => {
      saveRatio(broken, 0.5);
    }).not.toThrow();
    expect(loadRatio(undefined)).toBe(DEFAULT_RATIO);
  });
});
