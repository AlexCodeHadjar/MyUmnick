import { describe, expect, it } from "vitest";

import { messagesFor, type SkillData } from "../../core";
import { grouped, groupOf, needsConfirm, statsLine } from "./skills";

function skill(id: string, extra: Partial<SkillData> = {}): SkillData {
  return {
    id,
    plugin: id.split(".")[0] ?? id,
    title: id,
    summary: "",
    examples: [],
    network: false,
    gpu: false,
    enabled: true,
    loaded: true,
    uses: 0,
    average_ms: null,
    timeouts: 0,
    ...extra,
  };
}

describe("панель навыков", () => {
  it("группы: включены, выключены, не запущены — пустые не показываются", () => {
    const list = [
      skill("web_search", { loaded: false, enabled: false }),
      skill("tools.timer", { enabled: false }),
      skill("tools.time"),
    ];
    expect(grouped(list, "").map((part) => part.group)).toEqual(["on", "off", "idle"]);
    expect(groupOf(skill("w", { loaded: false }))).toBe("idle");
    expect(grouped([skill("a")], "").map((part) => part.group)).toEqual(["on"]);
  });

  it("поиск по названию, описанию и примерам без регистра", () => {
    const list = [
      skill("tools.timer", { title: "Таймер", examples: ["Поставь таймер на 5 минут"] }),
      skill("web_search.search", { title: "Поиск", summary: "Погода и новости" }),
    ];
    expect(grouped(list, "ПОГОДА")[0]?.skills.map((one) => one.id)).toEqual(["web_search.search"]);
    expect(grouped(list, "5 минут")[0]?.skills.map((one) => one.id)).toEqual(["tools.timer"]);
    expect(grouped(list, "нет такого")).toEqual([]);
  });

  it("интернет — только с подтверждением и только при включении", () => {
    expect(needsConfirm(skill("w", { network: true }), true)).toBe(true);
    expect(needsConfirm(skill("w", { network: true }), false)).toBe(false);
    expect(needsConfirm(skill("t"), true)).toBe(false);
  });

  it("счётчики на языке издания", () => {
    const t = messagesFor("ru");
    expect(statsLine(skill("t"), t)).toBe("");
    expect(statsLine(skill("t", { uses: 3, average_ms: 12.4, timeouts: 1 }), t)).toBe(
      `${t.skills.uses(3)} · ${t.skills.ms(12)} · ${t.skills.timeouts(1)}`,
    );
  });
});
