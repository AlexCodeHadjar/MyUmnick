import { describe, expect, it } from "vitest";

import { AvatarLoop, MAX_DELTA_MS, type FrameSource, type Visibility } from "./loop";

class ManualFrames implements FrameSource {
  readonly pending = new Map<number, (time: number) => void>();
  #next = 1;

  request(callback: (time: number) => void): number {
    const handle = this.#next++;
    this.pending.set(handle, callback);
    return handle;
  }

  cancel(handle: number): void {
    this.pending.delete(handle);
  }

  /** Отдать кадр с временем `time` всем ждущим. */
  frame(time: number): void {
    const callbacks = [...this.pending.values()];
    this.pending.clear();
    for (const callback of callbacks) {
      callback(time);
    }
  }
}

class ManualVisibility implements Visibility {
  isHidden = false;
  listener: (() => void) | null = null;

  hidden(): boolean {
    return this.isHidden;
  }

  onChange(listener: () => void): () => void {
    this.listener = listener;
    return () => {
      this.listener = null;
    };
  }

  set(hidden: boolean): void {
    this.isHidden = hidden;
    this.listener?.();
  }
}

function setup(): {
  loop: AvatarLoop;
  frames: ManualFrames;
  visibility: ManualVisibility;
  ticks: number[];
} {
  const frames = new ManualFrames();
  const visibility = new ManualVisibility();
  const ticks: number[] = [];
  const loop = new AvatarLoop((delta) => ticks.push(delta), frames, visibility);
  return { loop, frames, visibility, ticks };
}

describe("AvatarLoop", () => {
  it("шаг — время между кадрами; первый — нулевой", () => {
    const { loop, frames, ticks } = setup();
    loop.start();
    loop.start();
    frames.frame(1000);
    frames.frame(1016.5);
    frames.frame(1033);
    expect(ticks).toEqual([0, 16.5, 16.5]);
    expect(frames.pending.size).toBe(1);
  });

  it("подвисание — шаг ограничен", () => {
    const { loop, frames, ticks } = setup();
    loop.start();
    frames.frame(0);
    frames.frame(5000);
    expect(ticks).toEqual([0, MAX_DELTA_MS]);
  });

  it("скрытое окно — пауза, после показа шаг снова с нуля", () => {
    const { loop, frames, visibility, ticks } = setup();
    loop.start();
    frames.frame(0);
    visibility.set(true);
    expect(loop.running).toBe(false);
    expect(frames.pending.size).toBe(0);
    visibility.set(false);
    frames.frame(60_000);
    frames.frame(60_016);
    expect(ticks).toEqual([0, 0, 16]);
  });

  it("старт при скрытом окне ждёт показа", () => {
    const { loop, frames, visibility } = setup();
    visibility.isHidden = true;
    loop.start();
    expect(frames.pending.size).toBe(0);
    visibility.set(false);
    expect(frames.pending.size).toBe(1);
  });

  it("stop() отписывается и гасит кадр", () => {
    const { loop, frames, visibility } = setup();
    loop.start();
    loop.stop();
    expect(frames.pending.size).toBe(0);
    expect(visibility.listener).toBeNull();
  });

  it("исключение в tick не останавливает цикл", () => {
    const frames = new ManualFrames();
    const loop = new AvatarLoop(
      () => {
        throw new Error("кадр упал");
      },
      frames,
      new ManualVisibility(),
    );
    loop.start();
    expect(() => {
      frames.frame(0);
    }).toThrow("кадр упал");
    expect(frames.pending.size).toBe(1);
  });
});
