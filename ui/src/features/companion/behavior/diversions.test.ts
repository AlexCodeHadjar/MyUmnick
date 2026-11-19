import { describe, it, expect } from "vitest";
import { Diversions } from "./diversions";
describe("diversions", () => {
  it("rolls for a stumble once per walk", () => {
    const d = new Diversions(() => 0);
    expect(d.frame(1000, "walk", true, false)?.kind).toBe("trip");
    expect(d.frame(98000, "walk", true, false)).toBeNull();
  });
  it("interrupts scenes when the desktop becomes busy", () => {
    const d = new Diversions(() => 0);
    d.frame(0, "rest", true, true);
    expect(d.frame(130000, "rest", true, true)?.kind).toBe("peek");
    expect(d.frame(130001, "rest", false, true)).toBeNull();
  });
});
