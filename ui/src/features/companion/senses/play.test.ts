import { describe, expect, it } from "vitest";

import { caught, PlayWatch } from "./play";

const chest = { x: 500, y: 500 };

describe("игра с курсором", () => {
  it("быстрое кружение рядом — приглашение поиграть", () => {
    const watch = new PlayWatch();
    let playing = false;
    for (let i = 0; i < 40; i += 1) {
      const a = (i / 6) * Math.PI;
      playing =
        watch.feed(500 + Math.cos(a) * 150, 500 + Math.sin(a) * 150, i * 40, chest) || playing;
    }
    expect(playing).toBe(true);
  });

  it("пролетел мимо или медленно водит — не игра", () => {
    const pass = new PlayWatch();
    let flew = false;
    for (let i = 0; i < 30; i += 1) flew = pass.feed(100 + i * 60, 500, i * 40, chest) || flew;
    expect(flew).toBe(false);
    const slow = new PlayWatch();
    let lazy = false;
    for (let i = 0; i < 30; i += 1)
      lazy = slow.feed(500 + (i % 2) * 20, 500, i * 40, chest) || lazy;
    expect(lazy).toBe(false);
  });

  it("курсор у самой груди — поймал", () => {
    expect(caught(520, 510, chest)).toBe(true);
    expect(caught(600, 500, chest)).toBe(false);
  });
});
