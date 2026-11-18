/**
 * «Следовать за мной» и «не мешать печатать» (просьба пользователя 2026-11-18). Режим «следовать» —
 * за курсором: идёт к нему по опоре, лезет по краю экрана, если курсор выше, свисает с верха экрана,
 * если курсор там. Где бы пользователь ни печатал — отходит от поля ввода, в любом режиме.
 * Решения — чистые функции `space/chase.ts`; здесь — когда их применять.
 */
import type { Brain } from "../body";
import { cursorSpot, inTheWay, stepAside, worthMoving, type Point, type Rect } from "../space";
import type { Presence } from "./presence";

/** Как часто пересматривать место за курсором и как часто — у поля ввода. */
const TRACK_MS = 900;
const ASIDE_MS = 1500;
/** Курсор у самого персонажа (гладят, берут) — стоит на месте. */
const NEAR = 0.6;

export interface EscortState {
  /** Режим «следовать за мной». */
  follow: boolean;
  /** Можно двигаться: показан, стоит, не держат, не смотрит фильм, не тычет. */
  free: boolean;
}

export class Escort {
  readonly #brain: Brain;
  readonly #presence: Presence;
  /** Курсор и поле ввода (CSS-пиксели слоя) — от контроллера. */
  cursor: Point | null = null;
  caret: Rect | null = null;
  #trackAt = 0;
  #asideAt = 0;

  constructor(brain: Brain, presence: Presence) {
    this.#brain = brain;
    this.#presence = presence;
  }

  /** Раз в кадр. Вернёт `true`, если сам решил, куда идти (тогда остальное ждёт). */
  update(now: number, state: EscortState): boolean {
    if (!state.free) return false;
    if (this.caret !== null) return this.#keepOut(now, this.caret);
    return state.follow && this.#track(now);
  }

  /** Место рядом с курсором — для действия «следовать» «Разума». */
  target(): ReturnType<typeof cursorSpot> {
    const world = this.#presence.world;
    const brain = this.#brain;
    if (this.cursor === null || world === null) return null;
    const body = { x: brain.x, y: brain.y };
    return cursorSpot(brain.surfaceList, this.cursor, body, world.monitor, brain.figure);
  }

  #keepOut(now: number, caret: Rect): boolean {
    const brain = this.#brain;
    if (now < this.#asideAt || !inTheWay(caret, brain, brain.figure)) return true;
    this.#asideAt = now + ASIDE_MS;
    const spot = stepAside(brain.surfaceList, brain.spot, caret, brain.figure);
    if (spot !== null) brain.goTo(spot);
    return true;
  }

  #track(now: number): boolean {
    if (now < this.#trackAt || this.cursor === null) return false;
    this.#trackAt = now + TRACK_MS;
    const brain = this.#brain;
    const chest = { x: brain.x, y: brain.y - brain.chest };
    if (Math.hypot(this.cursor.x - chest.x, this.cursor.y - chest.y) < brain.figure * NEAR)
      return false;
    const spot = this.target();
    if (spot === null || !worthMoving(brain.spot, spot)) return false;
    brain.goTo(spot);
    return true;
  }
}
