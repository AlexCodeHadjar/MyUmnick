import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { AvatarRenderer, AvatarSource, StageSize } from "./AvatarRenderer";
import { AvatarSession, avatarSource, type AvatarStatus } from "./session";

class FakeRenderer implements AvatarRenderer {
  loaded: AvatarSource | null = null;
  readonly sizes: StageSize[] = [];
  readonly gaze: [number, number][] = [];
  updates = 0;
  disposed = false;
  failLoad: Error | null = null;

  load(source: AvatarSource): Promise<void> {
    this.loaded = source;
    return this.failLoad === null ? Promise.resolve() : Promise.reject(this.failLoad);
  }
  form = 0;
  readonly emotions: string[] = [];
  setEmotion(emotion: string): void {
    if (this.emotions.at(-1) !== emotion) this.emotions.push(emotion);
  }
  nod(): void {
    // Не нужен в этих тестах.
  }
  setSpeaking(): void {
    // Не нужен в этих тестах.
  }
  setMouthForm(form: number): void {
    this.form = form;
  }
  gesture(): void {
    // Не нужен в этих тестах.
  }
  contains(): boolean {
    return false;
  }
  setMouth(): void {
    // Не нужен в этих тестах.
  }
  lookAt(x: number, y: number): void {
    this.gaze.push([x, y]);
  }
  react(): void {
    // Не нужен в этих тестах.
  }
  update(): void {
    this.updates += 1;
  }
  resize(size: StageSize): void {
    this.sizes.push(size);
  }
  dispose(): void {
    this.disposed = true;
  }
}

/** Элемент сцены 800×600 в точке (100, 0) — без DOM. */
/* eslint-disable @typescript-eslint/consistent-type-assertions -- фейк DOM-элемента в тесте */
const host = {
  clientWidth: 800,
  clientHeight: 600,
  getBoundingClientRect: () => ({ left: 100, top: 0, width: 800, height: 600 }),
} as unknown as HTMLElement;
/* eslint-enable @typescript-eslint/consistent-type-assertions */

let observed: (() => void)[];
let frames: (() => void)[];

beforeEach(() => {
  observed = [];
  frames = [];
  vi.stubGlobal(
    "ResizeObserver",
    class {
      constructor(callback: () => void) {
        observed.push(callback);
      }
      observe(): void {
        // Колбэк зовёт тест.
      }
      disconnect(): void {
        observed.length = 0;
      }
    },
  );
  vi.stubGlobal("requestAnimationFrame", (callback: () => void) => frames.push(callback));
  vi.stubGlobal("cancelAnimationFrame", () => undefined);
  vi.stubGlobal("document", {
    hidden: false,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("avatarSource", () => {
  it("файлы модели — в /avatars/<имя>/", () => {
    expect(avatarSource("haru")).toEqual({
      modelUrl: "/avatars/haru/haru.model3.json",
      mappingUrl: "/avatars/haru/mapping.json",
    });
  });
});

describe("AvatarSession", () => {
  it("загрузка: размер сцены, модель, кадры, ресайз, взгляд", async () => {
    const renderer = new FakeRenderer();
    const statuses: AvatarStatus[] = [];
    const session = new AvatarSession(host, (s) => statuses.push(s));
    let created: StageSize | null = null;
    await session.start("haru", (_, size) => {
      created = size;
      return Promise.resolve(renderer);
    });
    expect(created).toEqual({ width: 800, height: 600 });
    expect(renderer.loaded?.modelUrl).toBe("/avatars/haru/haru.model3.json");
    expect(statuses.map((s) => s.state)).toEqual(["loading", "ready"]);

    frames.shift()?.();
    expect(renderer.updates).toBe(1);
    observed[0]?.();
    expect(renderer.sizes).toEqual([{ width: 800, height: 600 }]);
    session.lookAtPointer(500, 300);
    session.lookAhead();
    expect(renderer.gaze).toEqual([
      [0, 0],
      [0, 0],
    ]);

    session.dispose();
    expect(renderer.disposed).toBe(true);
    expect(session.renderer).toBeNull();
  });

  it("эмоция из mood доходит до рендера в каждом кадре", async () => {
    const renderer = new FakeRenderer();
    const session = new AvatarSession(host, () => undefined);
    await session.start("haru", () => Promise.resolve(renderer));
    session.activity = () => true;
    session.mood.set("happy");
    frames.shift()?.();
    expect(renderer.emotions).toEqual(["happy"]);
    session.dispose();
  });

  it("ошибка загрузки — статус с текстом для пользователя", async () => {
    const renderer = new FakeRenderer();
    renderer.failLoad = new Error("404");
    const statuses: AvatarStatus[] = [];
    await new AvatarSession(host, (s) => statuses.push(s)).start("haru", () =>
      Promise.resolve(renderer),
    );
    expect(statuses.at(-1)).toEqual({
      state: "error",
      message: "Модель «haru» не загрузилась: 404",
    });
  });

  it("закрыли сцену, пока создавался рендер — рендер освобождается сразу", async () => {
    const renderer = new FakeRenderer();
    const session = new AvatarSession(host, () => undefined);
    const started = session.start("haru", () => Promise.resolve(renderer));
    session.dispose();
    await started;
    expect(renderer.disposed).toBe(true);
    expect(renderer.loaded).toBeNull();
  });
});
