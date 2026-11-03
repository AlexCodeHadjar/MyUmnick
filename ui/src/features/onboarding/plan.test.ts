import { describe, expect, it } from "vitest";

import type { SetupData } from "../../core";
import {
  canInstall,
  downloadSize,
  formatSize,
  initialSelection,
  parseAvatars,
  percent,
  toggled,
  type SetupItem,
} from "./plan";

function item(id: string, overrides: Partial<SetupItem> = {}): SetupItem {
  return {
    id,
    title: id,
    license: "MIT",
    size: 100,
    required: false,
    recommended: false,
    installed: false,
    ...overrides,
  };
}

function setup(...items: SetupItem[]): SetupData {
  return {
    needed: true,
    gpu_total_mb: 16384,
    voices: ["xenia"],
    voice: "xenia",
    warnings: [],
    items,
  };
}

describe("выбор компонентов", () => {
  it("сначала выбрано рекомендованное и уже стоящее", () => {
    const data = setup(item("a", { recommended: true }), item("b"), item("c", { installed: true }));
    expect([...initialSelection(data)]).toEqual(["a", "c"]);
  });

  it("обязательное снять нельзя", () => {
    const required = item("a", { required: true });
    expect(toggled(new Set(["a"]), required).has("a")).toBe(true);
  });

  it("необязательное снимается и ставится", () => {
    const optional = item("b");
    expect(toggled(new Set(["b"]), optional).has("b")).toBe(false);
    expect(toggled(new Set(), optional).has("b")).toBe(true);
  });

  it("считается только то, что ещё качать", () => {
    const items = [
      item("a", { size: 10 }),
      item("b", { size: 20, installed: true }),
      item("c", { size: 40 }),
    ];
    expect(downloadSize(items, new Set(["a", "b"]))).toBe(10);
  });
});

describe("согласие", () => {
  it("без согласия загрузка не начинается", () => {
    const data = setup(item("a", { required: true }));
    expect(canInstall(data, new Set(["a"]), false)).toBe(false);
    expect(canInstall(data, new Set(["a"]), true)).toBe(true);
  });

  it("без обязательного загрузка не начинается", () => {
    const data = setup(item("a", { required: true }));
    expect(canInstall(data, new Set(), true)).toBe(false);
  });
});

describe("показ", () => {
  it("размеры", () => {
    expect(formatSize(7381381760)).toBe("6.9 ГБ");
    expect(formatSize(1024 ** 2 * 5)).toBe("5 МБ");
    expect(formatSize(10)).toBe("1 МБ");
  });

  it("проценты", () => {
    expect(percent(50, 200)).toBe(25);
    expect(percent(0, 0)).toBe(0);
    expect(percent(300, 200)).toBe(100);
  });

  it("аватары", () => {
    expect(parseAvatars(["a", "b"], "haru")).toEqual(["a", "b"]);
    expect(parseAvatars(null, "haru")).toEqual(["haru"]);
    expect(parseAvatars([], "haru")).toEqual(["haru"]);
    expect(parseAvatars([1], "haru")).toEqual(["haru"]);
  });
});
