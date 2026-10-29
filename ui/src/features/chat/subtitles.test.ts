import { describe, expect, it } from "vitest";

import type { ChatMessage, SpeechProgress } from "../../core";
import {
  readSubtitles,
  revealedLength,
  SPEECH_CHARS_PER_S,
  Subtitles,
  SUBTITLES_KEY,
  writeSubtitles,
} from "./subtitles";

const reply = (patch: Partial<ChatMessage> = {}): ChatMessage => ({
  id: 1,
  role: "assistant",
  text: "Привет! Рада тебя слышать, как дела?",
  turn: "t-1",
  status: "streaming",
  ...patch,
});

const speech = (patch: Partial<SpeechProgress> = {}): SpeechProgress => ({
  turn: "t-1",
  speaking: true,
  playedS: 0,
  receivedS: 0,
  ...patch,
});

const on = (s: SpeechProgress | null) => ({ enabled: true, speech: s });

describe("revealedLength", () => {
  it("режим выключен, реплика пользователя — текст целиком", () => {
    expect(revealedLength(reply(), { enabled: false, speech: speech() })).toBeNull();
    expect(revealedLength(reply({ role: "user", turn: null }), on(null))).toBeNull();
  });

  it("ответ идёт, звука ещё нет — текст ждёт голос", () => {
    expect(revealedLength(reply(), on(null))).toBe(0);
    expect(revealedLength(reply(), on(speech({ turn: "t-0" })))).toBe(0);
  });

  it("ход кончился без звука — показать текст, не прятать навсегда", () => {
    expect(revealedLength(reply({ status: "done" }), on(null))).toBeNull();
    expect(revealedLength(reply({ status: "cancelled" }), on(null))).toBeNull();
  });

  it("пока ход идёт — по темпу речи", () => {
    expect(revealedLength(reply(), on(speech({ playedS: 1 })))).toBe(SPEECH_CHARS_PER_S);
  });

  it("звук получен весь — точно по доле сыгранного", () => {
    const done = reply({ status: "done", text: "x".repeat(100) });
    expect(revealedLength(done, on(speech({ playedS: 2.5, receivedS: 10 })))).toBe(25);
    expect(revealedLength(done, on(speech({ playedS: 10, receivedS: 10 })))).toBe(100);
  });

  it("звук кончился — текст целиком; смолк посреди хода — ждём голос", () => {
    const silent = on(speech({ speaking: false, playedS: 1 }));
    expect(revealedLength(reply({ status: "done" }), silent)).toBeNull();
    expect(revealedLength(reply(), silent)).toBe(SPEECH_CHARS_PER_S);
  });
});

describe("Subtitles", () => {
  it("показанное не убывает при смене оценки", () => {
    const subtitles = new Subtitles();
    const message = reply({ text: "x".repeat(100) });
    expect(subtitles.text(message, on(speech({ playedS: 2 })))).toHaveLength(32);
    const done = { ...message, status: "done" as const };
    // Точная доля меньше оценки по темпу — субтитр не отматывается.
    expect(subtitles.text(done, on(speech({ playedS: 2, receivedS: 10 })))).toHaveLength(32);
    expect(subtitles.text(done, on(speech({ playedS: 5, receivedS: 10 })))).toHaveLength(50);
  });

  it("показанный целиком не прячется обратно", () => {
    const subtitles = new Subtitles();
    const message = reply();
    subtitles.text({ ...message, status: "done" }, on(speech({ speaking: false })));
    expect(subtitles.text(message, on(speech({ playedS: 0.1 })))).toBe(message.text);
  });
});

describe("настройка", () => {
  it("читается и пишется; без хранилища — выключено", () => {
    const store = new Map<string, string>();
    const storage = {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => {
        store.set(key, value);
      },
    };
    expect(readSubtitles(storage)).toBe(false);
    writeSubtitles(storage, true);
    expect(store.get(SUBTITLES_KEY)).toBe("on");
    expect(readSubtitles(storage)).toBe(true);
    expect(readSubtitles(undefined)).toBe(false);
  });
});
