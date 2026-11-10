import { describe, expect, it } from "vitest";

import { chatLabel, groupChats, readCollapsed, writeCollapsed } from "./groups";

const chat = (id: string, category: string | null, title = id) => ({
  id,
  title,
  category,
  updated: "2026-11-10T00:00:00+00:00",
});

describe("список чатов", () => {
  it("без категории — сверху, категории — по порядку, пустые тоже видны", () => {
    const groups = groupChats(
      [chat("a", null), chat("b", "games"), chat("c", "gone")],
      [
        { id: "games", name: "Игры" },
        { id: "work", name: "Работа" },
      ],
    );

    expect(groups.map((group) => group.category?.id ?? null)).toEqual([null, "games", "work"]);
    expect(groups[0]?.chats.map((one) => one.id)).toEqual(["a", "c"]);
    expect(groups[2]?.chats).toEqual([]);
  });

  it("пустое название — «Новый чат»", () => {
    expect(chatLabel(chat("x", null, " "), "Новый чат")).toBe("Новый чат");
    expect(chatLabel(chat("x", null, "Про котов"), "Новый чат")).toBe("Про котов");
  });

  it("свёрнутость запоминается, без хранилища — развёрнута", () => {
    const values = new Map<string, string>();
    const storage = {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
    };
    writeCollapsed(storage, true);

    expect(readCollapsed(storage)).toBe(true);
    expect(readCollapsed(null)).toBe(false);
  });
});
