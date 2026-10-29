import { describe, expect, it } from "vitest";

import { TypingDebouncer, type Timers } from "./typing";

/** Ручные таймеры: тест сам решает, когда «прошло время». */
class ManualTimers implements Timers {
  readonly pending = new Map<number, () => void>();
  #next = 1;

  set = (callback: () => void): number => {
    const id = this.#next++;
    this.pending.set(id, callback);
    return id;
  };

  clear = (id: number): void => {
    this.pending.delete(id);
  };

  fire(): void {
    for (const [id, callback] of [...this.pending]) {
      this.pending.delete(id);
      callback();
    }
  }
}

describe("TypingDebouncer", () => {
  it("уходит только последний черновик после паузы", () => {
    const timers = new ManualTimers();
    const sent: string[] = [];
    const typing = new TypingDebouncer((text) => sent.push(text), timers);

    typing.input("П");
    typing.input("Пр");
    typing.input("Привет");
    expect(sent).toEqual([]);
    expect(timers.pending.size).toBe(1);

    timers.fire();
    expect(sent).toEqual(["Привет"]);
  });

  it("отправка реплики отменяет ожидающий черновик", () => {
    const timers = new ManualTimers();
    const sent: string[] = [];
    const typing = new TypingDebouncer((text) => sent.push(text), timers);

    typing.input("Привет");
    typing.cancel();
    timers.fire();

    expect(sent).toEqual([]);
  });
});
