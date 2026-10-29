import { describe, expect, it } from "vitest";

import { AppStore } from "../../core";
import { isWaiting, type ConversationView } from "./reactions";

const view = (patch: Partial<ConversationView>): ConversationView => ({
  phase: "idle",
  connection: "open",
  lastRole: null,
  hasError: false,
  voiceExpected: false,
  voiceStarted: false,
  ...patch,
});

describe("isWaiting", () => {
  it("реплика ушла — ждём сразу, ещё до turn.started (T-17)", () => {
    expect(isWaiting(view({ lastRole: "user" }))).toBe(true);
  });

  it("без голоса: ход начат — ждём; пошли токены — ответ пришёл", () => {
    expect(isWaiting(view({ phase: "thinking", lastRole: "assistant" }))).toBe(true);
    expect(isWaiting(view({ phase: "speaking", lastRole: "assistant" }))).toBe(false);
    expect(isWaiting(view({ lastRole: "assistant" }))).toBe(false);
  });

  it("с голосом ответ пришёл, когда зазвучал, а не когда пошёл текст", () => {
    const voiced = { phase: "speaking", lastRole: "assistant", voiceExpected: true } as const;
    expect(isWaiting(view(voiced))).toBe(true);
    expect(isWaiting(view({ ...voiced, voiceStarted: true }))).toBe(false);
  });

  it("нет связи или ядро ответило ошибкой — не ждать вечно", () => {
    expect(isWaiting(view({ lastRole: "user", connection: "closed" }))).toBe(false);
    expect(isWaiting(view({ lastRole: "user", hasError: true }))).toBe(false);
  });

  it("store: ожидание в том же синхронном шаге, что и реплика", () => {
    const store = new AppStore();
    store.setConnection("open");
    store.addUserMessage("привет");
    expect(
      isWaiting(
        view({
          phase: store.phase,
          connection: store.connection,
          lastRole: store.messages.at(-1)?.role ?? null,
        }),
      ),
    ).toBe(true);
  });
});
