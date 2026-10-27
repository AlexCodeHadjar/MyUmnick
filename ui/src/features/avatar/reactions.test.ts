import { describe, expect, it } from "vitest";

import { AppStore } from "../../core";
import { reactionOf, type ConversationView } from "./reactions";

const view = (patch: Partial<ConversationView>): ConversationView => ({
  phase: "idle",
  connection: "open",
  lastRole: null,
  hasError: false,
  ...patch,
});

describe("reactionOf", () => {
  it("реплика ушла — «думаю» сразу, ещё до turn.started (T-17)", () => {
    expect(reactionOf(view({ lastRole: "user" }))).toBe("thinking");
  });

  it("ход начат — «думаю»; пошли токены — покой", () => {
    expect(reactionOf(view({ phase: "thinking", lastRole: "assistant" }))).toBe("thinking");
    expect(reactionOf(view({ phase: "speaking", lastRole: "assistant" }))).toBe("idle");
    expect(reactionOf(view({ lastRole: "assistant" }))).toBe("idle");
  });

  it("нет связи или ядро ответило ошибкой — не ждать вечно", () => {
    expect(reactionOf(view({ lastRole: "user", connection: "closed" }))).toBe("idle");
    expect(reactionOf(view({ lastRole: "user", hasError: true }))).toBe("idle");
  });

  it("store: «думаю» в том же синхронном шаге, что и реплика", () => {
    const store = new AppStore();
    store.setConnection("open");
    store.addUserMessage("привет");
    expect(
      reactionOf({
        phase: store.phase,
        connection: store.connection,
        lastRole: store.messages.at(-1)?.role ?? null,
        hasError: store.error !== null,
      }),
    ).toBe("thinking");
  });
});
