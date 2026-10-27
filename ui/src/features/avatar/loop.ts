/**
 * Цикл кадров аватара — вне реактивности Svelte (R-66): каждый кадр зовёт `tick(deltaMs)`,
 * при скрытом окне (свёрнуто, другая вкладка) останавливается и не тратит GPU.
 */

/** Шаг после паузы или подвисания ограничен: иначе физика волос «выстрелит» за один кадр. */
export const MAX_DELTA_MS = 100;

/** Источник кадров: в окне — `requestAnimationFrame`, в тестах — ручной. */
export interface FrameSource {
  request(callback: (time: number) => void): number;
  cancel(handle: number): void;
}

/** Видимость окна: `onChange` возвращает функцию отписки. */
export interface Visibility {
  hidden(): boolean;
  onChange(listener: () => void): () => void;
}

export const browserFrames: FrameSource = {
  request: (callback) => requestAnimationFrame(callback),
  cancel: (handle) => {
    cancelAnimationFrame(handle);
  },
};

export const browserVisibility: Visibility = {
  hidden: () => document.hidden,
  onChange(listener) {
    document.addEventListener("visibilitychange", listener);
    return () => {
      document.removeEventListener("visibilitychange", listener);
    };
  },
};

export class AvatarLoop {
  readonly #tick: (deltaMs: number) => void;
  readonly #frames: FrameSource;
  readonly #visibility: Visibility;
  #handle: number | null = null;
  #last: number | null = null;
  #unsubscribe: (() => void) | null = null;

  constructor(
    tick: (deltaMs: number) => void,
    frames: FrameSource = browserFrames,
    visibility: Visibility = browserVisibility,
  ) {
    this.#tick = tick;
    this.#frames = frames;
    this.#visibility = visibility;
  }

  get running(): boolean {
    return this.#handle !== null;
  }

  start(): void {
    if (this.#unsubscribe !== null) {
      return;
    }
    this.#unsubscribe = this.#visibility.onChange(() => {
      this.#sync();
    });
    this.#sync();
  }

  stop(): void {
    this.#unsubscribe?.();
    this.#unsubscribe = null;
    this.#pause();
  }

  #sync(): void {
    if (this.#visibility.hidden()) {
      this.#pause();
    } else if (this.#handle === null) {
      this.#schedule();
    }
  }

  #schedule(): void {
    this.#handle = this.#frames.request((time) => {
      this.#frame(time);
    });
  }

  #frame(time: number): void {
    // Первый кадр после старта или паузы — нулевой шаг: время паузы анимации не принадлежит.
    const delta = this.#last === null ? 0 : Math.min(MAX_DELTA_MS, Math.max(0, time - this.#last));
    this.#last = time;
    this.#schedule();
    this.#tick(delta);
  }

  #pause(): void {
    if (this.#handle !== null) {
      this.#frames.cancel(this.#handle);
      this.#handle = null;
    }
    this.#last = null;
  }
}
