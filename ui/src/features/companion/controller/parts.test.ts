import { describe, expect, it } from "vitest";

import { Brain } from "../body";
import { Gestures } from "./gestures";
import { Speech } from "./speech";

describe("облачко", () => {
  it("своя реплика висит 6 с; позвали — «слушаю»; новый ответ ассистента узнаётся", () => {
    const speech = new Speech();
    speech.say("Привет!", 0);
    expect(speech.text(1000, "слушаю")).toBe("Привет!");
    expect(speech.own(1000)).toBe(true);
    expect(speech.text(7000, "слушаю")).toBe("");
    speech.call(8000);
    expect(speech.text(8500, "слушаю")).toBe("слушаю");
    speech.reply("Длинный ответ ассистента", 9000);
    expect(speech.reply("Новый", 9100)).toBe(true);
  });
});

describe("жесты", () => {
  it("короткий клик — погладить; повели — держат; удержали — прицел", () => {
    const brain = new Brain(() => 0.5);
    const pets: number[] = [];
    const gestures = new Gestures(brain, {
      pet: (now) => pets.push(now),
      held: () => undefined,
      released: () => undefined,
    });
    gestures.down(100, 100, 0);
    gestures.up({ x: 100, y: 100, shift: false, ctrl: false }, 50);
    expect(pets).toEqual([50]);
    gestures.down(100, 100, 100);
    gestures.move(130, 100, 120);
    expect(gestures.gesture).toBe("held");
    gestures.cancel();
    gestures.down(100, 100, 200);
    gestures.tick(400);
    expect(gestures.gesture).toBe("aim");
  });
});
