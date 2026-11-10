import { describe, expect, it } from "vitest";

import {
  afterPick,
  DEFAULT_LAUNCHER,
  editionById,
  EDITIONS,
  keyAction,
  needsAgeGate,
  needsPicker,
  parseLauncher,
} from "./editions";
import { pickRequested } from "./launcher";

const EN = editionById("en");
const RU = editionById("ru");

describe("экран выбора издания", () => {
  it("две плитки: русская и английская 18+", () => {
    expect(EDITIONS.map((edition) => edition.id)).toEqual(["ru", "en"]);
    expect(EN.badge).toBe("18+");
    expect(RU.adult).toBe(false);
  });

  it("битое состояние — умолчания, а не сбой", () => {
    expect(parseLauncher(null)).toEqual(DEFAULT_LAUNCHER);
    expect(parseLauncher({ last: "de", remember: "yes" })).toEqual(DEFAULT_LAUNCHER);
    expect(parseLauncher({ last: "en", remember: true, adultConfirmed: "2026-11-10" })).toEqual({
      last: "en",
      remember: true,
      adultConfirmed: "2026-11-10",
    });
  });

  it("экран показывается, пока выбор не запомнен, и по явной просьбе", () => {
    expect(needsPicker(DEFAULT_LAUNCHER, false)).toBe(true);
    expect(needsPicker({ ...DEFAULT_LAUNCHER, remember: true }, false)).toBe(false);
    expect(needsPicker({ ...DEFAULT_LAUNCHER, remember: true }, true)).toBe(true);
    expect(pickRequested("?pick=1")).toBe(true);
    expect(pickRequested("")).toBe(false);
  });

  it("подтверждение возраста — один раз и только для английского", () => {
    expect(needsAgeGate(EN, DEFAULT_LAUNCHER)).toBe(true);
    expect(needsAgeGate(RU, DEFAULT_LAUNCHER)).toBe(false);
    const confirmed = afterPick(DEFAULT_LAUNCHER, EN, false, "2026-11-10");
    expect(confirmed).toEqual({ last: "en", remember: false, adultConfirmed: "2026-11-10" });
    expect(needsAgeGate(EN, confirmed)).toBe(false);
    expect(afterPick(confirmed, RU, true, "2026-12-01").adultConfirmed).toBe("2026-11-10");
  });

  it("клавиши: стрелки по кругу, Enter и цифры — запуск", () => {
    expect(keyAction("ArrowRight", 1, 2)).toEqual({ kind: "focus", index: 0 });
    expect(keyAction("ArrowLeft", 0, 2)).toEqual({ kind: "focus", index: 1 });
    expect(keyAction("Enter", 1, 2)).toEqual({ kind: "start", index: 1 });
    expect(keyAction("2", 0, 2)).toEqual({ kind: "start", index: 1 });
    expect(keyAction("3", 0, 2)).toBeNull();
    expect(keyAction("a", 0, 2)).toBeNull();
  });
});
