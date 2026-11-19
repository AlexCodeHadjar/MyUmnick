import { afterEach, describe, expect, it, vi } from "vitest";

import { RadioPlayer } from "./player";

/** Поддельный `<audio>`: `play()` ждёт, пока тест решит, завёлся ли поток. */
class FakeAudio {
  static all: FakeAudio[] = [];
  src = "";
  volume = 1;
  preload = "";
  crossOrigin: string | null = null;
  paused = true;
  #settle: ((ok: boolean) => void) | null = null;

  constructor() {
    FakeAudio.all.push(this);
  }

  play(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.#settle = (ok) => {
        if (ok) {
          this.paused = false;
          resolve();
        } else reject(new Error("no source"));
      };
    });
  }

  settle(ok: boolean): void {
    this.#settle?.(ok);
  }

  pause(): void {
    this.paused = true;
  }

  removeAttribute(): void {
    this.src = "";
  }

  load(): void {
    // Нечего грузить без `src`.
  }
}

async function flush(): Promise<void> {
  for (let i = 0; i < 5; i++) await Promise.resolve();
}

afterEach(() => {
  vi.unstubAllGlobals();
  FakeAudio.all = [];
});

describe("радио: переключение станций", () => {
  it("быстрое переключение не оставляет второй поток", async () => {
    vi.stubGlobal("Audio", FakeAudio);
    vi.stubGlobal("AudioContext", undefined);
    const player = new RadioPlayer(undefined);
    void player.play();
    const first = FakeAudio.all[0];
    player.select(1);
    // Первая станция не завелась с анализом — старая попытка не должна заводить её без анализа.
    first?.settle(false);
    await flush();
    // Оба оставшихся потока заводятся: новая станция и (в старом коде) запасная попытка старой.
    for (const one of FakeAudio.all.slice(1)) one.settle(true);
    await flush();
    const playing = FakeAudio.all.filter((one) => !one.paused);
    expect(playing).toHaveLength(1);
    player.off();
    expect(FakeAudio.all.every((one) => one.paused)).toBe(true);
  });

  it("поток, заведшийся после выключения, глушится", async () => {
    vi.stubGlobal("Audio", FakeAudio);
    vi.stubGlobal("AudioContext", undefined);
    const player = new RadioPlayer(undefined);
    void player.play();
    player.off();
    FakeAudio.all[0]?.settle(true);
    await flush();
    expect(FakeAudio.all.every((one) => one.paused)).toBe(true);
    expect(player.mode).toBe("off");
  });
});
