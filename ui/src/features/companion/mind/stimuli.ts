/**
 * Стимулы (MIND §3.3, «разрешители» Блумберга): событие не командует действием, а на время поднимает
 * оценку подходящих. Сила затухает линейно за `lifeS`; память короткая — старое не влияет.
 */
export type Stimulus = "focus" | "desktop" | "pet" | "comeback" | "browser";

const MEMORY = 8;

interface Entry {
  kind: Stimulus;
  at: number;
  strength: number;
  lifeS: number;
}

export class Stimuli {
  #entries: Entry[] = [];

  add(kind: Stimulus, now: number, strength = 1, lifeS = 20): void {
    this.#entries = [
      ...this.#entries.filter((one) => one.kind !== kind),
      { kind, at: now, strength, lifeS },
    ];
    if (this.#entries.length > MEMORY) this.#entries.shift();
  }

  /** Текущая сила стимула 0…1. */
  level(kind: Stimulus, now: number): number {
    const entry = this.#entries.find((one) => one.kind === kind);
    if (entry === undefined) return 0;
    return Math.max(0, entry.strength * (1 - (now - entry.at) / entry.lifeS));
  }

  /** Стимул «использован» действием — больше его не тянет. */
  consume(kind: Stimulus): void {
    this.#entries = this.#entries.filter((one) => one.kind !== kind);
  }
}
