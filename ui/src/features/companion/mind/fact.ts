/**
 * Сглаженный факт картины мира (MIND §3.1): становится правдой, если сырой сигнал продержался
 * `onS` секунд, и ложью — если пропал на `offS`. Мимолётное (быстрый Alt+Tab, видео на секунду) не
 * меняет поведение.
 */
export class Fact {
  readonly #onS: number;
  readonly #offS: number;
  #value = false;
  #since = 0;
  #pendingSince: number | null = null;

  constructor(onS: number, offS: number) {
    this.#onS = onS;
    this.#offS = offS;
  }

  get value(): boolean {
    return this.#value;
  }

  /** Сколько секунд факт в нынешнем значении (на момент `now`). */
  age(now: number): number {
    return now - this.#since;
  }

  update(raw: boolean, now: number): boolean {
    if (raw === this.#value) {
      this.#pendingSince = null;
      return this.#value;
    }
    this.#pendingSince ??= now;
    if (now - this.#pendingSince >= (raw ? this.#onS : this.#offS)) {
      this.#value = raw;
      this.#since = now;
      this.#pendingSince = null;
    }
    return this.#value;
  }
}
