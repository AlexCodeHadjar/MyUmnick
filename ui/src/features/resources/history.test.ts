import { describe, expect, it } from "vitest";

import type { ResourcesData } from "../../core";
import { addSnapshot, HISTORY_POINTS, sparkline, stateLabel, type LoadHistory } from "./history";

function snapshot(...models: [string, string, number][]): ResourcesData {
  return {
    limit_mb: 4000,
    capacity_mb: 4000,
    free_mb: 1000,
    pinned: [{ name: "llm", vram_mb: 8900 }],
    models: models.map(([name, state, vram_mb]) => ({
      name,
      state,
      vram_mb,
      priority: "tool",
      users: 0,
      waiting_reason: null,
    })),
  };
}

describe("история нагрузки", () => {
  it("новый инструмент появляется сам", () => {
    const history: LoadHistory = new Map();
    addSnapshot(history, snapshot(["код", "in_use", 3000]));
    addSnapshot(history, snapshot(["код", "in_use", 3000], ["слух", "idle", 500]));
    expect([...history.keys()]).toEqual(["код", "слух"]);
  });

  it("память занимает только загруженная модель", () => {
    const history: LoadHistory = new Map();
    addSnapshot(history, snapshot(["код", "unloaded", 3000]));
    addSnapshot(history, snapshot(["код", "waiting", 3000]));
    addSnapshot(history, snapshot(["код", "in_use", 3000]));
    addSnapshot(history, snapshot(["код", "idle", 3000]));
    expect(history.get("код")).toEqual([0, 0, 3000, 3000]);
  });

  it("история ограничена", () => {
    const history: LoadHistory = new Map();
    for (let i = 0; i < HISTORY_POINTS + 5; i += 1) {
      addSnapshot(history, snapshot(["код", "idle", 100]));
    }
    expect(history.get("код")).toHaveLength(HISTORY_POINTS);
  });
});

describe("график", () => {
  it("новые точки справа, ноль внизу, максимум наверху", () => {
    const points = sparkline([0, 100], 100, [299, 20]);
    expect(points).toBe("298.0,20.0 299.0,0.0");
  });

  it("без лимита не делит на ноль", () => {
    expect(sparkline([0], 0, [299, 20])).toBe("299.0,20.0");
  });
});

describe("состояние", () => {
  it("известное — по-русски, неизвестное — как есть", () => {
    expect(stateLabel("waiting")).toBe("ждёт");
    expect(stateLabel("новое")).toBe("новое");
  });
});
