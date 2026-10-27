import { describe, expect, it } from "vitest";

import { FIRST_CHAR_SPAN } from "../../core";
import { isMetricsHotkey } from "./hotkey";
import { overBudget, percentile, summarize, summarizeAll } from "./stats";

describe("percentile", () => {
  it("ближайший ранг", () => {
    const sorted = Array.from({ length: 100 }, (_, i) => i + 1);
    expect(percentile(sorted, 50)).toBe(50);
    expect(percentile(sorted, 95)).toBe(95);
    expect(percentile([7], 95)).toBe(7);
    expect(percentile([1, 2], 50)).toBe(1);
    expect(percentile([], 50)).toBeNaN();
  });
});

describe("summarize", () => {
  it("последний — по порядку прихода, перцентили — по значениям", () => {
    const summary = summarize("llm.first_token", [300, 100, 200]);
    expect(summary).toEqual({
      name: "llm.first_token",
      last: 200,
      p50: 200,
      p95: 300,
      count: 3,
      budget: 250,
    });
    expect(overBudget(summary)).toBe(false);
    expect(overBudget(summarize("llm.first_token", [400, 300]))).toBe(true);
    expect(overBudget(summarize("llm.stream", [9999]))).toBe(false);
  });

  it("стадии с нормой — выше, остальные по имени", () => {
    const rows = summarizeAll({ "zz.other": [1], "llm.stream": [2], [FIRST_CHAR_SPAN]: [3] });
    expect(rows.map((r) => r.name)).toEqual([FIRST_CHAR_SPAN, "llm.stream", "zz.other"]);
  });
});

describe("isMetricsHotkey", () => {
  const base = { code: "KeyM", ctrlKey: true, shiftKey: true, altKey: false, metaKey: false };

  it("Ctrl+Shift+M в любой раскладке", () => {
    expect(isMetricsHotkey(base)).toBe(true);
    expect(isMetricsHotkey({ ...base, shiftKey: false })).toBe(false);
    expect(isMetricsHotkey({ ...base, altKey: true })).toBe(false);
    expect(isMetricsHotkey({ ...base, code: "KeyN" })).toBe(false);
  });
});
