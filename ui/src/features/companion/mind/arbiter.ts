/**
 * Арбитр действий (MIND §3.4): utility AI с защитой от метаний — группы важности, минимальная длительность,
 * инерция текущего, порог переключения, падение интереса, перезарядка, пауза «осмотреться» и медленный
 * личный шум. Чистый класс — проверяется тестами.
 */
export type Band = 0 | 1 | 2 | 3;

export interface Activity<C> {
  id: string;
  /** 3 — слушает, 2 — режимы, 1 — выходки, 0 — покой. Важнее — прерывает сразу. */
  band: Band;
  /** Не меньше стольких секунд, если не прервала группа важнее. */
  minS: number;
  /** После конца столько секунд не выбирается снова. */
  cooldownS: number;
  /** Падение интереса в секунду, пока идёт (Блумберг): 0 — не надоедает. */
  boredom: number;
  /** Разовое (фраза, тычок, прыжок): заканчивается само через `minS`. */
  oneShot: boolean;
  score(context: C, now: number): number;
}

export interface Choice {
  id: string;
  changed: boolean;
  previous: string;
}

const INERTIA = 1.25;
const MARGIN = 0.1;
const INTERRUPT = 0.5;
const NOISE = 0.04;
const NOISE_EVERY_S = 30;

export class Arbiter<C> {
  readonly #list: readonly Activity<C>[];
  readonly #random: () => number;
  #current: Activity<C>;
  #startedAt = 0;
  #done = false;
  #settleUntil = 0;
  readonly #ended = new Map<string, number>();
  #noise = new Map<string, number>();
  #noiseAt = -Infinity;

  /** `list[0]` — покой: действие по умолчанию. */
  constructor(list: readonly Activity<C>[], random: () => number = Math.random) {
    const idle = list[0];
    if (idle === undefined) throw new Error("Нужно хотя бы одно действие — покой");
    this.#list = list;
    this.#current = idle;
    this.#random = random;
  }

  get current(): string {
    return this.#current.id;
  }

  /** Сколько секунд идёт текущее действие. */
  elapsed(now: number): number {
    return now - this.#startedAt;
  }

  /** Дошёл, допрыгнул — `seconds` осматривается: выходки 1-й группы не начинаются. */
  settle(now: number, seconds: number): void {
    this.#settleUntil = Math.max(this.#settleUntil, now + seconds);
  }

  /** Текущее действие закончилось само — со следующей оценки выбирается новое. */
  finish(): void {
    this.#done = true;
  }

  choose(context: C, now: number): Choice {
    this.#refreshNoise(now);
    const current = this.#current;
    const elapsed = now - this.#startedAt;
    if (current.oneShot && elapsed >= current.minS) this.#done = true;
    const own = this.#score(current, context, now);
    const done = this.#done || own <= 0.01;
    const interest = Math.max(0.2, 1 - current.boredom * elapsed);
    const incumbent = done ? 0 : own * interest * INERTIA;
    let best: Activity<C> | null = null;
    let bestScore = 0;
    for (const one of this.#list) {
      if (one === current) continue;
      const score = this.#available(one, now) ? this.#score(one, context, now) : 0;
      if (score > bestScore) {
        best = one;
        bestScore = score;
      }
    }
    const urgent = best !== null && best.band > current.band && bestScore >= INTERRUPT;
    const ripe = done || elapsed >= current.minS;
    const better = bestScore > incumbent + MARGIN;
    if (best === null || !(urgent || (ripe && better))) {
      return { id: current.id, changed: false, previous: current.id };
    }
    this.#ended.set(current.id, now);
    this.#current = best;
    this.#startedAt = now;
    this.#done = false;
    return { id: best.id, changed: true, previous: current.id };
  }

  #available(one: Activity<C>, now: number): boolean {
    const ended = this.#ended.get(one.id);
    if (ended !== undefined && now - ended < one.cooldownS) return false;
    return !(one.band === 1 && now < this.#settleUntil);
  }

  #score(one: Activity<C>, context: C, now: number): number {
    const raw = one.score(context, now);
    if (raw <= 0) return 0;
    return Math.min(1, Math.max(0, raw + (this.#noise.get(one.id) ?? 0)));
  }

  /** Личный шум: раз в 30 с, а не каждый кадр — разнообразие без метаний. */
  #refreshNoise(now: number): void {
    if (now - this.#noiseAt < NOISE_EVERY_S) return;
    this.#noiseAt = now;
    this.#noise = new Map(this.#list.map((one) => [one.id, (this.#random() - 0.5) * 2 * NOISE]));
  }
}
