/**
 * Черновик реплики для speculative prefill (T-05): ядру уходит последний текст поля после паузы
 * в наборе, а не каждое нажатие — прогрев на каждую букву только занял бы LLM. Отправка реплики
 * отменяет ожидающий черновик: он устарел.
 */

/** Пауза в наборе, после которой черновик уходит ядру, мс (T-05: ~300). */
export const TYPING_DEBOUNCE_MS = 300;

export interface Timers {
  set: (callback: () => void, ms: number) => number;
  clear: (id: number) => void;
}

const windowTimers: Timers = {
  set: (callback, ms) => window.setTimeout(callback, ms),
  clear: (id) => {
    window.clearTimeout(id);
  },
};

export class TypingDebouncer {
  readonly #send: (text: string) => void;
  readonly #timers: Timers;
  readonly #delayMs: number;
  #pending: number | null = null;

  constructor(
    send: (text: string) => void,
    timers: Timers = windowTimers,
    delayMs = TYPING_DEBOUNCE_MS,
  ) {
    this.#send = send;
    this.#timers = timers;
    this.#delayMs = delayMs;
  }

  /** Поле изменилось: черновик уйдёт, если `delayMs` не будет новых изменений. */
  input(text: string): void {
    this.cancel();
    this.#pending = this.#timers.set(() => {
      this.#pending = null;
      this.#send(text);
    }, this.#delayMs);
  }

  /** Реплика отправлена или поле ушло: ожидающий черновик не нужен. */
  cancel(): void {
    if (this.#pending !== null) {
      this.#timers.clear(this.#pending);
      this.#pending = null;
    }
  }
}
