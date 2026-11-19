import { describe, expect, it } from "vitest";
import { DesktopReactions } from "./desktopEvents";

describe("DesktopReactions", () => {
  it("drops blocked signals and enforces the cooldown after a reaction", () => {
    const effects = new DesktopReactions();
    const event = { kind: "copy", size: 0 } as const;
    expect(effects.offer(event, 0, false, 0)).toBeNull();
    expect(effects.offer(event, 10, true, 0.999)).toBe("hug_paper");
    expect(effects.offer(event, 20, true, 0)).toBeNull();
    expect(effects.offer(event, 120_000, true, 0)).toBe("hug_paper");
  });

  it("keeps a separate cooldown per kind: a download does not mute the save stamp", () => {
    const effects = new DesktopReactions();
    expect(effects.offer({ kind: "download", size: 1 }, 0, true, 0)).toBe("carry_box");
    expect(effects.offer({ kind: "paste", size: 0 }, 10, true, 0)).toBe("stamp");
    expect(effects.offer({ kind: "paste", size: 0 }, 20, true, 0)).toBeNull();
  });
});
