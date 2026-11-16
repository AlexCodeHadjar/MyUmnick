import { describe, expect, it } from "vitest";

import { messagesFor } from "../../core";
import {
  BUILT_IN,
  DEFAULT_THEME,
  deletePreset,
  fromHex,
  loadPresets,
  loadTheme,
  parseTheme,
  pointOf,
  savePreset,
  saveTheme,
  swatchAt,
  themeVars,
  toHex,
} from "./palette";

function memory(): Storage {
  const map = new Map<string, string>();
  return {
    get length() {
      return map.size;
    },
    clear: () => {
      map.clear();
    },
    getItem: (key) => map.get(key) ?? null,
    key: (index) => [...map.keys()][index] ?? null,
    removeItem: (key) => {
      map.delete(key);
    },
    setItem: (key, value) => {
      map.set(key, value);
    },
  };
}

describe("цветовой круг", () => {
  it("красный сверху, по часовой: справа — 90°, снизу — 180°; центр — без насыщенности", () => {
    expect(swatchAt(0, -100, 100)).toEqual({ h: 0, s: 1 });
    expect(swatchAt(100, 0, 100).h).toBeCloseTo(90);
    expect(swatchAt(0, 50, 100)).toEqual({ h: 180, s: 0.5 });
    expect(swatchAt(0, 0, 100).s).toBe(0);
    expect(swatchAt(500, 0, 100).s).toBe(1);
  });

  it("маркер стоит туда, откуда взят цвет", () => {
    const point = pointOf({ h: 90, s: 0.5 }, 100);
    expect(point.x).toBeCloseTo(50);
    expect(point.y).toBeCloseTo(0);
    const back = swatchAt(point.x, point.y, 100);
    expect(back.h).toBeCloseTo(90);
    expect(back.s).toBeCloseTo(0.5);
  });

  it("HEX туда и обратно; не цвет — null", () => {
    expect(toHex({ h: 0, s: 1 })).toBe("#ff3333");
    const swatch = fromHex("#33ff99");
    expect(swatch?.h).toBeCloseTo(150);
    expect(swatch?.s).toBeCloseTo(1);
    expect(fromHex("зелёный")).toBeNull();
  });
});

describe("тема", () => {
  it("все переменные theme.css и цвета ролей из своих маркеров", () => {
    const vars = themeVars(DEFAULT_THEME);
    for (const name of ["--ground", "--panel", "--rule", "--title", "--value", "--hot", "--text"]) {
      expect(vars[name]).toMatch(/^hsl\(/);
    }
    expect(vars["--value"]).toBe("hsl(155 85% 65%)");
    expect(vars["--hot"]).toBe("hsl(36 100% 64%)");
    expect(vars["--panel"]).toContain("/ 96%");
  });

  it("серый основной цвет — серый фон", () => {
    const vars = themeVars({ ...DEFAULT_THEME, main: { h: 200, s: 0 } });
    expect(vars["--ground"]).toMatch(/^hsl\(200 0% /);
  });

  it("сохраняется и читается; битое — по умолчанию", () => {
    const storage = memory();
    expect(loadTheme(storage)).toEqual(DEFAULT_THEME);
    const theme = { ...DEFAULT_THEME, depth: 0.7 };
    saveTheme(storage, theme);
    expect(loadTheme(storage)).toEqual(theme);
    storage.setItem("vtuber.theme", "{oops");
    expect(loadTheme(storage)).toEqual(DEFAULT_THEME);
    expect(
      parseTheme({ main: { h: 400, s: 2 }, value: { h: 0, s: 0 }, hot: { h: 0, s: 0 }, depth: 5 }),
    ).toEqual({ main: { h: 40, s: 1 }, value: { h: 0, s: 0 }, hot: { h: 0, s: 0 }, depth: 1 });
  });

  it("свои палитры: сохранить, заменить по имени, удалить; встроенные остаются", () => {
    const storage = memory();
    savePreset(storage, " Моя ", DEFAULT_THEME);
    const replaced = savePreset(storage, "Моя", { ...DEFAULT_THEME, depth: 1 });
    expect(replaced.filter((p) => !p.builtIn)).toEqual([
      { name: "Моя", theme: { ...DEFAULT_THEME, depth: 1 }, builtIn: false },
    ]);
    expect(deletePreset(storage, "Моя")).toEqual([...BUILT_IN]);
    expect(loadPresets(storage)).toHaveLength(BUILT_IN.length);
  });

  it("у встроенных палитр есть подписи на обоих языках", () => {
    for (const lang of ["ru", "en"] as const) {
      const names = new Map<string, string>(Object.entries(messagesFor(lang).theme.presets));
      for (const preset of BUILT_IN) expect(names.get(preset.name)).toBeTruthy();
    }
  });
});
