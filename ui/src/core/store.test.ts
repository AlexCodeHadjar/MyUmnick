import { beforeEach, describe, expect, it } from "vitest";

import type { OutboundMessage } from "./protocol.gen";
import { AppStore, SPAN_HISTORY } from "./store.svelte";

const T1 = "t-000001";
const T2 = "t-000002";

const started = (turn: string): OutboundMessage => ({ v: 1, type: "turn.started", turn, data: {} });
const delta = (turn: string, text: string): OutboundMessage => ({
  v: 1,
  type: "chat.delta",
  turn,
  data: { text },
});
const finished = (turn: string): OutboundMessage => ({
  v: 1,
  type: "turn.finished",
  turn,
  data: {},
});
const cancelled = (turn: string): OutboundMessage => ({
  v: 1,
  type: "turn.cancelled",
  turn,
  data: { reason: "new_message", message: "" },
});

let store: AppStore;

beforeEach(() => {
  store = new AppStore();
});

describe("ход", () => {
  it("started → delta → finished собирает ответ", () => {
    store.addUserMessage("привет");
    store.apply(started(T1));
    expect(store.phase).toBe("thinking");
    expect(store.turn).toBe(T1);
    store.apply(delta(T1, "При"));
    store.apply(delta(T1, "вет!"));
    expect(store.phase).toBe("speaking");
    store.apply(finished(T1));
    expect(store.phase).toBe("idle");
    expect(store.turn).toBeNull();
    expect(store.messages.map(({ role, text, status }) => [role, text, status])).toEqual([
      ["user", "привет", "done"],
      ["assistant", "Привет!", "done"],
    ]);
    expect(new Set(store.messages.map((m) => m.id)).size).toBe(2);
  });

  it("сбой показывает причину рядом с пометкой, обычная отмена — нет", () => {
    store.apply(started(T1));
    store.apply({
      v: 1,
      type: "turn.cancelled",
      turn: T1,
      data: { reason: "error", message: "Картинки не поддерживаются" },
    });
    expect(store.messages.at(-1)?.text).toBe("Картинки не поддерживаются");
    expect(store.messages.at(-1)?.status).toBe("cancelled");

    store.apply(started(T2));
    store.apply(delta(T2, "Нач"));
    store.apply({
      v: 1,
      type: "turn.cancelled",
      turn: T2,
      data: { reason: "new_message", message: "" },
    });
    expect(store.messages.at(-1)?.text).toBe("Нач");
  });

  it("отмена помечает ответ, поздние дельты отменённого хода отбрасываются", () => {
    store.apply(started(T1));
    store.apply(delta(T1, "Начало"));
    store.addUserMessage("стой");
    store.apply(cancelled(T1));
    store.apply(delta(T1, " хвост"));
    store.apply(started(T2));
    store.apply(delta(T1, " ещё хвост"));
    store.apply(delta(T2, "Новый"));
    expect(store.messages.map(({ text, status }) => [text, status])).toEqual([
      ["Начало", "cancelled"],
      ["стой", "done"],
      ["Новый", "streaming"],
    ]);
  });

  it("сообщения чужого хода не трогают текущий", () => {
    store.apply(started(T2));
    store.apply(finished(T1));
    store.apply(cancelled(T1));
    store.apply({ v: 1, type: "avatar.emotion", turn: T1, data: { emotion: "sad", intensity: 1 } });
    expect(store.turn).toBe(T2);
    expect(store.emotion).toBe("neutral");
    store.apply({
      v: 1,
      type: "avatar.emotion",
      turn: T2,
      data: { emotion: "happy", intensity: 1 },
    });
    expect(store.emotion).toBe("happy");
  });

  it("новый turn.started без конца прошлого закрывает прошлый как отменённый", () => {
    store.apply(started(T1));
    store.apply(started(T2));
    expect(store.messages.map((m) => m.status)).toEqual(["cancelled", "streaming"]);
  });

  it("разрыв связи посреди хода отменяет ход", () => {
    store.apply(started(T1));
    store.setConnection("connecting");
    expect(store.turn).toBe(T1);
    store.setConnection("closed");
    expect(store.connection).toBe("closed");
    expect(store.phase).toBe("idle");
    expect(store.messages[0]?.status).toBe("cancelled");
  });
});

describe("служебные сообщения", () => {
  it("status, metrics.span, error", () => {
    expect(store.backends).toEqual({ llm: "unknown", tts: "unknown", stt: "unknown" });
    store.apply({ v: 1, type: "status", data: { component: "llm", state: "ready" } });
    store.apply({ v: 1, type: "metrics.span", turn: null, data: { name: "llm.ttft", ms: 95 } });
    store.apply({
      v: 1,
      type: "error",
      turn: null,
      data: { code: "llm_unavailable", message: "LLM недоступна" },
    });
    expect(store.backends.llm).toBe("ready");
    expect(store.spans).toEqual({ "llm.ttft": [95] });
    expect(store.error?.code).toBe("llm_unavailable");
    store.addUserMessage("ещё раз");
    expect(store.error).toBeNull();
  });
});

describe("замеры", () => {
  it("история стадии ограничена, старые вытесняются", () => {
    for (let i = 0; i < SPAN_HISTORY + 5; i += 1) {
      store.recordSpan("ui.first_char", i);
    }
    const history = store.spans["ui.first_char"] ?? [];
    expect(history).toHaveLength(SPAN_HISTORY);
    expect(history[0]).toBe(5);
    expect(history.at(-1)).toBe(SPAN_HISTORY + 4);
  });
});

describe("голосовой ввод", () => {
  it("гипотеза показывается, финальная фраза становится репликой", () => {
    const store = new AppStore();
    store.apply({ v: 1, type: "input.hypothesis", data: { text: "как де" } });
    expect(store.hypothesis).toBe("как де");
    store.apply({ v: 1, type: "input.final", data: { text: "как дела" } });
    expect(store.hypothesis).toBe("");
    expect(store.messages.map((m) => [m.role, m.text])).toEqual([["user", "как дела"]]);
  });
});

describe("издание", () => {
  it("app.edition запоминается и переключает язык интерфейса", async () => {
    const { locale } = await import("./i18n");
    store.apply({
      v: 1,
      type: "app.edition",
      data: { id: "en", language: "en", content_profile: "unfiltered", stream_safe: false },
    });

    expect(store.edition?.id).toBe("en");
    expect(locale.lang).toBe("en");
    expect(locale.t.composer.send).toBe("Send");
    locale.set("ru");
  });
});
