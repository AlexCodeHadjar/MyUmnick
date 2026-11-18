import { describe, expect, it } from "vitest";

import { findTarget, quotedNames } from "./pointer";

const rect = { x: 0, y: 0, w: 10, h: 10 };

describe("покажи на экране", () => {
  it("находит названия в кавычках разных видов", () => {
    expect(quotedNames('Нажмите «Сохранить», затем "Settings" и “Экспорт”.')).toEqual([
      "Сохранить",
      "Settings",
      "Экспорт",
    ]);
    expect(quotedNames("Без кавычек ничего нет")).toEqual([]);
  });

  it("выбирает видимый элемент: точное совпадение лучше частичного", () => {
    const targets = [
      { name: "Сохранить как", rect, kind: "button" },
      { name: "Сохранить", rect, kind: "button" },
      { name: "Настройки профиля", rect, kind: "link" },
    ];
    expect(findTarget(targets, ["сохранить"])?.name).toBe("Сохранить");
    expect(findTarget(targets, ["Настройки"])?.name).toBe("Настройки профиля");
    expect(findTarget(targets, ["Удалить"])).toBeNull();
  });
});
