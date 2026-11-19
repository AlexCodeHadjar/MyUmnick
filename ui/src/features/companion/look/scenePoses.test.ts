import { describe, expect, it } from "vitest";
import { pickFrame } from "./pack";
import { placement, tallness } from "./placement";

const quiet = { time: 0, mouth: 0, speaking: false, blink: null };

describe("кадры сцен FRAMES-6", () => {
  it("одноразовая сцена идёт кадр за кадром от начала позы и держит последний", () => {
    // База — копия кадра удара (как у этапов 2026-11-19): в порядок не вставляется.
    const have = new Set(["stand", "stamp", "stamp_1", "stamp_2", "stamp_3"]);
    expect(pickFrame("stamp", { ...quiet, since: 0 }, have)).toBe("stamp_1");
    expect(pickFrame("stamp", { ...quiet, since: 0.2 }, have)).toBe("stamp_2");
    expect(pickFrame("stamp", { ...quiet, since: 9 }, have)).toBe("stamp_3");
  });

  it("только базовый кадр (пакет пользователя) — он и показывается", () => {
    const have = new Set(["stand", "hug_paper"]);
    expect(pickFrame("hug_paper", { ...quiet, since: 5 }, have)).toBe("hug_paper");
  });

  it("нет кадров сцены — прежняя поза (пакет пользователя)", () => {
    const have = new Set(["stand", "wave", "walk_1", "walk_2"]);
    expect(pickFrame("knock", quiet, have)).toBe("wave");
    expect(pickFrame("chase", quiet, have)).toBe("walk_1");
  });
});

describe("высокий кадр", () => {
  it("рисуется в том же масштабе, опора на том же месте, лишнее — сверху", () => {
    const normal = placement(1, [0.5, 0.97], 768, 1);
    const tall = placement(1, [0.5, 0.97], 768, tallness({ height: 912 }, 768));
    expect(tall.h).toBeCloseTo(912);
    // Низ кадра ниже опоры на столько же пикселей, что и у обычного.
    expect(tall.cy + tall.h / 2).toBeCloseTo(normal.cy + normal.h / 2);
  });

  it("подвешенная поза (опора сверху) растёт вниз: точка хвата на месте", () => {
    const normal = placement(1, [0.5, 0.06], 768, 1);
    const tall = placement(1, [0.5, 0.06], 768, 1.2);
    // Верх кадра выше опоры на столько же пикселей, что и у обычного.
    expect(tall.cy - tall.h / 2).toBeCloseTo(normal.cy - normal.h / 2);
  });

  it("пакет без кадра stand или обычный кадр — без поправки", () => {
    expect(tallness({ height: 900 }, null)).toBe(1);
    expect(tallness({ height: 760 }, 768)).toBe(1);
  });
});
