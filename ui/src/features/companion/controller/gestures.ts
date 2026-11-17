/**
 * Мышь над спутником (как у Capri): короткий клик — погладить, сразу повели — «держат», удержали на
 * месте — прицел молнии. Только состояние жеста и его исход; что делает тело — `Brain`.
 */
import type { Brain, Effect } from "../body";
import { dropTarget, release, velocityOf, type Spot } from "../space";

const HOLD_MS = 150;
const MOVE_PX = 6;

export type Gesture = "none" | "held" | "aim";

interface Point {
  x: number;
  y: number;
  t: number;
}

export interface GestureHooks {
  /** Короткий клик — погладили. */
  pet(now: number): void;
  /** Держат и двигают: для «трясут» (T4). */
  held(x: number, y: number, now: number): void;
  /** Отпустили с этой скоростью: «бросили» (T5). */
  released(speed: number, now: number): void;
}

export class Gestures {
  readonly #brain: Brain;
  readonly #hooks: GestureHooks;
  #press: Point | null = null;
  #gesture: Gesture = "none";
  #aim: { x: number; y: number; ghost: Spot | null } | null = null;
  #trail: Point[] = [];
  #drop: Spot | null = null;

  constructor(brain: Brain, hooks: GestureHooks) {
    this.#brain = brain;
    this.#hooks = hooks;
  }

  get gesture(): Gesture {
    return this.#gesture;
  }

  /** Жест идёт — клики слоя не отпускать сквозь. */
  get active(): boolean {
    return this.#gesture !== "none";
  }

  down(x: number, y: number, now: number): void {
    this.#press = { x, y, t: now };
    this.#trail = [{ x, y, t: now }];
    this.#brain.wake();
  }

  move(x: number, y: number, now: number): void {
    const press = this.#press;
    if (press === null) return;
    this.#trail = [...this.#trail.filter((p) => now - p.t < 200), { x, y, t: now }];
    if (this.#gesture === "none" && Math.hypot(x - press.x, y - press.y) > MOVE_PX) {
      this.#gesture = "held";
      this.#brain.hold(x, y);
    }
    const target = dropTarget(this.#brain.surfaceList, x, y);
    if (this.#gesture === "held") {
      this.#brain.moveHeld(x, y);
      this.#hooks.held(x, y, now);
      this.#drop = target;
    } else if (this.#gesture === "aim") {
      this.#aim = { x: target?.x ?? x, y: target?.y ?? y, ghost: target };
    }
  }

  up(point: { x: number; y: number; shift: boolean; ctrl: boolean }, now: number): void {
    if (this.#press === null) return;
    if (this.#gesture === "held") this.#releaseHeld(point, now);
    else if (this.#gesture === "none") this.#hooks.pet(now);
    else this.#fireBolt();
    this.cancel();
  }

  /** Esc или конец жеста. */
  cancel(): void {
    this.#press = null;
    this.#gesture = "none";
    this.#aim = null;
    this.#drop = null;
    this.#trail = [];
  }

  /** Раз в кадр: удержали на месте — прицел молнии. */
  tick(now: number): void {
    const press = this.#press;
    if (press === null || this.#gesture !== "none" || now - press.t < HOLD_MS) return;
    this.#gesture = "aim";
    this.#aim = { x: press.x, y: press.y, ghost: null };
  }

  /** Подсказки жеста для отрисовки: кольцо «закрепится здесь» и молния прицела. */
  effects(): Effect[] {
    const out: Effect[] = [];
    const mark = this.#gesture === "held" ? this.#drop : (this.#aim?.ghost ?? null);
    if (mark !== null) out.push({ kind: "mark", x: mark.x, y: mark.y, t: 0 });
    const aim = this.#aim;
    const brain = this.#brain;
    if (aim !== null) {
      out.push({ kind: "bolt", from: [brain.x, brain.y - brain.chest], to: [aim.x, aim.y], t: 0 });
    }
    return out;
  }

  #releaseHeld(point: { x: number; y: number; shift: boolean; ctrl: boolean }, now: number): void {
    const velocity = velocityOf(this.#trail);
    this.#hooks.released(Math.hypot(velocity.vx, velocity.vy), now);
    const done = release(this.#brain.surfaceList, point, velocity);
    if (done.kind === "place") this.#brain.place(done.spot);
    else if (done.kind === "hang") this.#brain.hang(done.x, done.y);
    else this.#brain.toss(done.vx, done.vy);
  }

  /** Отпустили прицел на самом персонаже — отмена; иначе — разряд по молнии к цели. */
  #fireBolt(): void {
    const aim = this.#aim;
    const brain = this.#brain;
    if (aim === null) return;
    if (Math.hypot(aim.x - brain.x, aim.y - (brain.y - brain.chest)) > 60) {
      brain.bolt(aim.ghost, [aim.x, aim.y]);
    }
  }
}
