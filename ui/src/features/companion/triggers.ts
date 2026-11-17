/**
 * Триггеры спутника (BEHAVIOR §3): события мыши, окна-хозяина и времени → реакция с перезарядкой.
 * Здесь только распознавание — чистые классы и функции, проверяются тестами; реакции — `Companion.svelte`.
 * Клавиатуру и клики по чужим окнам не слушаем (BEHAVIOR §3, T19–T20): только положение курсора.
 */
export type Trigger =
  | "dizzy"
  | "toss"
  | "greet"
  | "comeback"
  | "stare"
  | "flinch"
  | "drag"
  | "homeless"
  | "back"
  | "night"
  | "stretch";

/** Перезарядка, секунды: реакция не чаще (таблица BEHAVIOR §3). */
const COOLDOWN_S: Record<Trigger, number> = {
  dizzy: 20,
  toss: 15,
  greet: 600,
  comeback: 600,
  stare: 180,
  flinch: 60,
  drag: 60,
  homeless: 60,
  back: 300,
  night: 3600,
  stretch: 3000,
};

export class Cooldowns {
  readonly #last = new Map<Trigger, number>();

  /** Можно ли сработать сейчас (`now` — секунды); да — перезарядка начинается. */
  ready(kind: Trigger, now: number): boolean {
    const last = this.#last.get(kind);
    if (last !== undefined && now - last < COOLDOWN_S[kind]) return false;
    this.#last.set(kind, now);
    return true;
  }
}

const AWAY_S = 600;
const BREAK_S = 300;
const WORK_S = 3000;
const STARE_S = 4;
const STARE_PX = 120;
const FLINCH_PX = 150;
const FLINCH_SPEED = 3000;

/** Курсор: возвращение после отсутствия (T7), «смотрит» (T8), рывок рядом (T9), долгая работа (T17). */
export class CursorWatch {
  #prev: { x: number; y: number; t: number } | null = null;
  #lastMove = 0;
  #activeSince = 0;
  #hoverSince: number | null = null;

  /** Положение курсора `x, y` в момент `t` (с); `body` — грудь спутника или `null`, пока его нет. */
  feed(x: number, y: number, t: number, body: { x: number; y: number } | null): Trigger[] {
    const out: Trigger[] = [];
    const prev = this.#prev;
    this.#prev = { x, y, t };
    if (prev === null) {
      this.#lastMove = t;
      this.#activeSince = t;
      return out;
    }
    const distance = Math.hypot(x - prev.x, y - prev.y);
    if (distance > 2) {
      const away = t - this.#lastMove;
      if (away >= AWAY_S) out.push("comeback");
      if (away >= BREAK_S) this.#activeSince = t;
      this.#lastMove = t;
      const speed = distance / Math.max(0.01, t - prev.t);
      if (body !== null && speed > FLINCH_SPEED && near(x, y, body, FLINCH_PX)) out.push("flinch");
    }
    if (t - this.#activeSince >= WORK_S && t - this.#lastMove < 60) out.push("stretch");
    if (body === null || !near(x, y, body, STARE_PX)) {
      this.#hoverSince = null;
    } else {
      this.#hoverSince ??= t;
      if (t - this.#hoverSince >= STARE_S) out.push("stare");
    }
    return out;
  }
}

function near(x: number, y: number, body: { x: number; y: number }, radius: number): boolean {
  return Math.hypot(x - body.x, y - body.y) < radius;
}

/** Трясут мышью (T4): за последнюю секунду три и больше разворота на скорости больше 1500 px/с. */
export function shaken(trail: readonly { x: number; y: number; t: number }[]): boolean {
  const last = trail.at(-1);
  if (last === undefined) return false;
  const recent = trail.filter((p) => last.t - p.t <= 1000);
  let sign = 0;
  let turns = 0;
  for (let i = 1; i < recent.length; i += 1) {
    const a = recent[i - 1];
    const b = recent[i];
    if (a === undefined || b === undefined || b.t <= a.t) continue;
    const vx = ((b.x - a.x) / (b.t - a.t)) * 1000;
    if (Math.abs(vx) < 1500) continue;
    const next = Math.sign(vx);
    if (sign !== 0 && next !== sign) turns += 1;
    sign = next;
  }
  return turns >= 3;
}

/** Окно-хозяина таскают быстро (T10): скорость сдвига больше 600 px/с. */
export function dragged(
  before: { x: number; y: number },
  after: { x: number; y: number },
  seconds: number,
): boolean {
  return seconds > 0 && Math.hypot(after.x - before.x, after.y - before.y) / seconds > 600;
}

/** Ночь (T16): с часа до пяти. */
export function lateNight(hour: number): boolean {
  return hour >= 1 && hour < 5;
}
