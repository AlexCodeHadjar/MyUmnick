import { describe, expect, it } from "vitest";

import { DEFAULT_MAPPING, expressionFor, MappingError, parseMapping } from "./mapping";

const HARU_LIKE = {
  version: 1,
  expressions: {
    Normal: "e/Normal.exp3.json",
    Smile: "e/Smile.exp3.json",
    Think: "e/f02.exp3.json",
  },
  emotions: { neutral: "Normal", happy: "Smile", thinking: "Think" },
  reactions: { thinking: { expression: "Think", motion: { group: "Tap", index: 2 } } },
  frame: { zoom: 1.55, offsetY: 0.3 },
};

describe("parseMapping", () => {
  it("полный маппинг; пропущенные сдвиги кадра — 0", () => {
    const mapping = parseMapping(HARU_LIKE);
    expect(mapping.emotions.happy).toBe("Smile");
    expect(mapping.reactions.thinking).toEqual({
      expression: "Think",
      motion: { group: "Tap", index: 2 },
    });
    expect(mapping.frame).toEqual({ zoom: 1.55, offsetX: 0, offsetY: 0.3 });
  });

  it("минимальный маппинг — пустые разделы, кадр по умолчанию", () => {
    expect(parseMapping({ version: 1 })).toEqual(DEFAULT_MAPPING);
  });

  it.each([
    ["не объект", [], "корень"],
    ["другая версия", { version: 2 }, "version"],
    ["выражение не .exp3.json", { version: 1, expressions: { A: "a.png" } }, "expressions.A"],
    ["неизвестная эмоция", { version: 1, emotions: { joyful: "A" } }, "emotions.joyful"],
    ["эмоция без выражения", { version: 1, emotions: { happy: "Нет" } }, "emotions.happy"],
    ["неизвестная реакция", { version: 1, reactions: { dancing: {} } }, "reactions.dancing"],
    [
      "дробный индекс моушена",
      { version: 1, reactions: { thinking: { motion: { group: "Tap", index: 1.5 } } } },
      "reactions.thinking.motion.index",
    ],
    [
      "группа моушена не строка",
      { version: 1, reactions: { idle: { motion: { group: 1, index: 0 } } } },
      "reactions.idle.motion.group",
    ],
    ["масштаб вне диапазона", { version: 1, frame: { zoom: 0 } }, "frame.zoom"],
    ["сдвиг не число", { version: 1, frame: { offsetY: "0.3" } }, "frame.offsetY"],
  ])("ошибка называет поле: %s", (_, raw, field) => {
    expect(() => parseMapping(raw)).toThrow(MappingError);
    expect(() => parseMapping(raw)).toThrow(field);
  });
});

describe("expressionFor", () => {
  const mapping = parseMapping(HARU_LIKE);

  it("реакция важнее эмоции; без реакции — эмоция; нет ни того ни другого — null", () => {
    expect(expressionFor(mapping, "happy", "thinking")).toBe("Think");
    expect(expressionFor(mapping, "happy", "idle")).toBe("Smile");
    expect(expressionFor(mapping, "sad", "idle")).toBeNull();
    expect(expressionFor(DEFAULT_MAPPING, "happy", "thinking")).toBeNull();
  });
});
