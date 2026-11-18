import { describe, expect, it } from "vitest";

import { commandOf, suggest, type Command } from "./commands";

const LIST: Command[] = [
  { id: "private", name: "private", hint: "" },
  { id: "clear", name: "clear", hint: "" },
];

describe("команды чата", () => {
  it("«/» показывает все команды, «/pr» — подходящую", () => {
    expect(suggest("/", LIST).map((one) => one.id)).toEqual(["private", "clear"]);
    expect(suggest("/pr", LIST).map((one) => one.id)).toEqual(["private"]);
  });

  it("обычный текст и текст с пробелом — без подсказок", () => {
    expect(suggest("привет", LIST)).toEqual([]);
    expect(suggest("/private на", LIST)).toEqual([]);
  });

  it("набранная команда узнаётся, незнакомая — нет", () => {
    expect(commandOf(" /Clear ", LIST)?.id).toBe("clear");
    expect(commandOf("/nope", LIST)).toBeNull();
    expect(commandOf("clear", LIST)).toBeNull();
  });
});
