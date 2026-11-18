/**
 * Плавность движения кодом, без лишних кадров (ANIMATION.md): плавный разворот, наклон по скорости,
 * упругая посадка, растворение при смене кадра. Только состояние и числа — рисует `stage.ts`.
 */
import type { Body } from "../body";
import type { Pose } from "../space";

/** Разворот — за 0,16 с; растворение кадра — 150 мс; упругость посадки — 0,22 с. */
const TURN_RATE = 1 / 0.16;
const FADE_S = 0.15;
const LAND_S = 0.22;
const MAX_LEAN = 0.09;
/** Смена позы — «выдох-вдох» (критик, раунд 2): старая гаснет со сжатием, потом новая с растяжкой. */
const OUT_S = 0.06;
const IN_S = 0.08;
/** Широкие позы — разворот не уже 0,6: иначе лежащая фигура сплющивается в полоску. */
const WIDE: ReadonlySet<Pose> = new Set([
  "laydown",
  "sleep",
  "sit_corner",
  "sit_edge",
  "perch_corner",
  "watch",
  "jukebox",
]);
/** Циклы, где кадры отличаются только телом: в них растворение уместно. Лицо меняется — резко. */
export const SOFT_LOOPS: ReadonlySet<Pose> = new Set([
  "stand",
  "sit_edge",
  "perch_corner",
  "lean_side",
  "hang_side",
  "sit_corner",
  "laydown",
  "sleep",
  "held",
  "float",
  "radio_idle",
  "jukebox",
]);

/** Этап смены позы: старая уходит (`out`) или новая приходит (`in`), `k` — 0…1. */
export interface Swap {
  phase: "out" | "in";
  k: number;
}

export interface Pose2D {
  /** Показанное направление: от −1 до 1 (в середине разворота — узкая фигура). */
  scaleX: number;
  /** Сжатие по высоте при посадке (1 — нет). */
  scaleY: number;
  /** Наклон, радианы. */
  lean: number;
}

export class Motion {
  #facing = 1;
  #lean = 0;
  #land = 1;
  #lastX: number | null = null;
  #lastPhase = "";
  #fade = 1;
  /** Прошлый кадр, который растворяется поверх нового, и его поза (своя точка опоры). */
  previous: ImageBitmap | null = null;
  previousPose: Pose | null = null;
  #current: ImageBitmap | null = null;
  #currentPose: Pose | null = null;
  #fadeS = FADE_S;
  /** Сменилась поза (а не кадр цикла). */
  poseChange = false;
  #swapT = Infinity;
  #snapTurn = false;

  /** Идёт переход — нужно 60 кадров/с. */
  get busy(): boolean {
    // Растворение кадров плавно и при 20 кадрах/с (стресс-прогон 2026-11-17: иначе цикл дыхания
    // держал 60 кадров/с постоянно) — 60 нужны только развороту и посадке.
    return this.#land < 1 || Math.abs(this.#facing) < 0.999 || this.swap !== null;
  }

  /** Идёт смена позы «выдох-вдох» — что рисовать. */
  get swap(): Swap | null {
    if (this.previous === null || !this.poseChange) return null;
    if (this.#swapT < OUT_S) return { phase: "out", k: this.#swapT / OUT_S };
    if (this.#swapT < OUT_S + IN_S) return { phase: "in", k: (this.#swapT - OUT_S) / IN_S };
    return null;
  }

  /** Сколько осталось от прошлого кадра (0 — растворился). */
  get fadeLeft(): number {
    return this.previous === null ? 0 : 1 - this.#fade;
  }

  /**
   * Кадр этого шага: сменился — начать растворение прошлого. `loopS` — длительность кадра цикла: внутри
   * цикла растворение не длиннее половины кадра (критик: иначе ноги «мажутся»); 0 — без растворения.
   */
  frame(image: ImageBitmap | null, pose: Pose, loopS: number): void {
    if (image === this.#current) return;
    this.poseChange = pose !== this.#currentPose;
    this.previous = this.#current;
    this.previousPose = this.#currentPose;
    this.#current = image;
    this.#currentPose = pose;
    // Смена позы: последовательно (`swap`), без наложения; разворот в этот же миг — мгновенно, его
    // маскирует смена позы. Кадр цикла: короткое растворение только у «телесных» циклов.
    this.#swapT = this.poseChange && this.previous !== null ? 0 : Infinity;
    this.#snapTurn = this.poseChange;
    this.#fadeS = this.poseChange || !SOFT_LOOPS.has(pose) ? 0 : Math.min(FADE_S, loopS / 2);
    this.#fade = this.previous === null || this.#fadeS <= 0 ? 1 : 0;
  }

  step(body: Body, dt: number): Pose2D {
    this.#fade = this.#fadeS <= 0 ? 1 : Math.min(1, this.#fade + dt / this.#fadeS);
    this.#swapT += dt;
    if (this.#fade >= 1 && this.swap === null) this.previous = null;
    this.#turn(body.facing, dt);
    this.#tilt(body, dt);
    this.#landing(body.phase, dt);
    const squash = Math.sin(Math.PI * this.#land) * (1 - this.#land);
    const ease = Math.sin((Math.PI / 2) * Math.abs(this.#facing));
    return {
      // Мягче (критик: ×0,35 при смене позы — грубо).
      scaleX:
        Math.sign(this.#facing || 1) * Math.max(this.#narrowest(), ease) * (1 + squash * 0.25),
      scaleY: 1 - squash * 0.2,
      lean: this.#lean,
    };
  }

  #narrowest(): number {
    return this.#currentPose !== null && WIDE.has(this.#currentPose) ? 0.6 : 0.08;
  }

  /** Разворот с замедлением — через узкую фигуру, как поворот, а не зеркало. */
  #turn(target: 1 | -1, dt: number): void {
    if (this.#snapTurn) {
      this.#snapTurn = false;
      this.#facing = target;
      return;
    }
    const step = TURN_RATE * 2 * dt;
    const delta = target - this.#facing;
    this.#facing = Math.abs(delta) <= step ? target : this.#facing + Math.sign(delta) * step;
  }

  /** Наклон по горизонтальной скорости — в ходьбе, прыжке, полёте; в покое выпрямляется. */
  #tilt(body: Body, dt: number): void {
    const moving = body.phase === "walk" || body.phase === "jump" || body.phase === "fall";
    const vx = this.#lastX === null || dt <= 0 ? 0 : (body.x - this.#lastX) / dt;
    this.#lastX = body.x;
    const windup = body.phase === "walk" && Math.abs(vx) < 1 ? body.facing * 0.05 : 0;
    const target = moving ? Math.max(-MAX_LEAN, Math.min(MAX_LEAN, vx / 2500 + windup)) : 0;
    this.#lean += (target - this.#lean) * Math.min(1, dt * 8);
  }

  /** Упал или допрыгнул до опоры — короткое упругое сжатие. */
  #landing(phase: string, dt: number): void {
    if (phase === "rest" && (this.#lastPhase === "fall" || this.#lastPhase === "jump"))
      this.#land = 0;
    this.#lastPhase = phase;
    this.#land = Math.min(1, this.#land + dt / LAND_S);
  }
}
