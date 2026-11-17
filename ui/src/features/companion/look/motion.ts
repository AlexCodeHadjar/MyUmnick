/**
 * Плавность движения кодом, без лишних кадров (ANIMATION.md): плавный разворот, наклон по скорости,
 * упругая посадка, растворение при смене кадра. Только состояние и числа — рисует `stage.ts`.
 */
import type { Body } from "../body";

/** Разворот — за 0,16 с; растворение кадра — 150 мс; упругость посадки — 0,22 с. */
const TURN_RATE = 1 / 0.16;
const FADE_S = 0.15;
const LAND_S = 0.22;
const MAX_LEAN = 0.09;

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
  /** Прошлый кадр, который растворяется поверх нового. */
  previous: ImageBitmap | null = null;
  #current: ImageBitmap | null = null;

  /** Идёт переход — нужно 60 кадров/с. */
  get busy(): boolean {
    // Растворение кадров плавно и при 20 кадрах/с (стресс-прогон 2026-11-17: иначе цикл дыхания
    // держал 60 кадров/с постоянно) — 60 нужны только развороту и посадке.
    return this.#land < 1 || Math.abs(this.#facing) < 0.999;
  }

  /** Сколько осталось от прошлого кадра (0 — растворился). */
  get fadeLeft(): number {
    return this.previous === null ? 0 : 1 - this.#fade;
  }

  /** Кадр этого шага: сменился — начать растворение прошлого. */
  frame(image: ImageBitmap | null): void {
    if (image === this.#current) return;
    this.previous = this.#current;
    this.#current = image;
    this.#fade = this.previous === null ? 1 : 0;
  }

  step(body: Body, dt: number): Pose2D {
    this.#fade = Math.min(1, this.#fade + dt / FADE_S);
    if (this.#fade >= 1) this.previous = null;
    this.#turn(body.facing, dt);
    this.#tilt(body, dt);
    this.#landing(body.phase, dt);
    const squash = Math.sin(Math.PI * this.#land) * (1 - this.#land);
    const ease = Math.sin((Math.PI / 2) * Math.abs(this.#facing));
    return {
      scaleX: Math.sign(this.#facing || 1) * Math.max(0.08, ease) * (1 + squash * 0.5),
      scaleY: 1 - squash * 0.35,
      lean: this.#lean,
    };
  }

  /** Разворот с замедлением — через узкую фигуру, как поворот, а не зеркало. */
  #turn(target: 1 | -1, dt: number): void {
    const step = TURN_RATE * 2 * dt;
    const delta = target - this.#facing;
    this.#facing = Math.abs(delta) <= step ? target : this.#facing + Math.sign(delta) * step;
  }

  /** Наклон по горизонтальной скорости — в ходьбе, прыжке, полёте; в покое выпрямляется. */
  #tilt(body: Body, dt: number): void {
    const moving = body.phase === "walk" || body.phase === "jump" || body.phase === "fall";
    const vx = this.#lastX === null || dt <= 0 ? 0 : (body.x - this.#lastX) / dt;
    this.#lastX = body.x;
    const target = moving ? Math.max(-MAX_LEAN, Math.min(MAX_LEAN, vx / 2500)) : 0;
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
