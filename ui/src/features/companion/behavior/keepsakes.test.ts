import { describe, expect, it } from "vitest";
import { addItem, dayProgress, parsePocket } from "./keepsakes";

const item = { name: "photo.png", icon: "AQID" };

describe("keepsakes", () => {
  it("keeps unique recent display items within the pocket limit", () => {
    const items = Array.from({ length: 20 }, (_, i) => ({ ...item, name: String(i) }));
    expect(addItem(items, item)).toHaveLength(12);
    expect(addItem([item], item)).toEqual([item]);
  });

  it("discards damaged storage and starts each local day afresh", () => {
    expect(parsePocket("{broken")).toEqual([]);
    expect(parsePocket('[{"name":3}]')).toEqual([]);
    expect(dayProgress({ day: "yesterday", seconds: 500 }, "today", 4)).toEqual({
      day: "today",
      seconds: 4,
    });
  });
});
