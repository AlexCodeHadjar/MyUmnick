import { describe, expect, it } from "vitest";

import { backendIndicator, connectionIndicator } from "./status";

describe("connectionIndicator", () => {
  it("первое подключение и потеря связи — разные тексты", () => {
    expect(connectionIndicator("connecting", false).label).toBe("подключение…");
    expect(connectionIndicator("closed", false).tone).toBe("wait");
    expect(connectionIndicator("connecting", true).label).toBe("нет связи — переподключаюсь");
    expect(connectionIndicator("closed", true).tone).toBe("bad");
    expect(connectionIndicator("open", true).tone).toBe("ok");
    expect(connectionIndicator("replaced", true).tone).toBe("off");
  });
});

describe("backendIndicator", () => {
  it("без связи состояние бэкенда неизвестно", () => {
    expect(backendIndicator("ready", true)).toEqual({ label: "готов", tone: "ok" });
    expect(backendIndicator("ready", false)).toEqual({ label: "—", tone: "off" });
    expect(backendIndicator("failed", true).tone).toBe("bad");
    expect(backendIndicator("loading", true).tone).toBe("wait");
  });
});
