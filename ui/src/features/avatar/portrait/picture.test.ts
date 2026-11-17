import { describe, expect, it } from "vitest";

import { messagesFor } from "../../../core";
import { portraitPose } from "./PortraitRenderer";
import { MAX_PICTURE_BYTES, parseFit, pictureProblem } from "./picture";

const t = messagesFor("ru");

describe("картинка персонажа", () => {
  it("принимает PNG, JPEG, WebP, GIF до 20 МБ", () => {
    expect(pictureProblem({ type: "image/png", size: 1000 }, t)).toBeNull();
    expect(pictureProblem({ type: "image/gif", size: MAX_PICTURE_BYTES }, t)).toBeNull();
    expect(pictureProblem({ type: "image/bmp", size: 1000 }, t)).toBe(t.character.badType);
    expect(pictureProblem({ type: "image/png", size: MAX_PICTURE_BYTES + 1 }, t)).toBe(
      t.character.tooBig,
    );
    expect(pictureProblem({ type: "image/png", size: 0 }, t)).toBe(t.character.broken);
  });

  it("способ вписать: неизвестное — целиком", () => {
    expect(parseFit("cover")).toBe("cover");
    expect(parseFit("contain")).toBe("contain");
    expect(parseFit("stretch")).toBe("corner");
    expect(parseFit(null)).toBe("corner");
  });
});

describe("жизнь картинки", () => {
  const still = { time: 0, mouth: 0, pulse: 0, lookX: 0, lookY: 0 };

  it("дыхание — в пределах процента с небольшим, без речи картинка на месте", () => {
    for (const time of [0, 0.8, 1.75, 2.6]) {
      const pose = portraitPose({ ...still, time });
      expect(pose.scaleY).toBeGreaterThanOrEqual(1);
      expect(pose.scaleY).toBeLessThanOrEqual(1.013);
      expect(pose.lift).toBeCloseTo(0);
    }
  });

  it("речь и вспышка поднимают картинку, курсор наклоняет", () => {
    expect(portraitPose({ ...still, mouth: 1 }).lift).toBeLessThan(-5);
    expect(portraitPose({ ...still, pulse: 1 }).lift).toBeLessThan(-7);
    const pose = portraitPose({ ...still, lookX: 1, lookY: -1 });
    expect(pose.tiltY).toBeGreaterThan(0);
    expect(pose.tiltX).toBeLessThan(0);
  });
});
