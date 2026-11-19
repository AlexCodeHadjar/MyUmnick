import type { Rect } from "../space";
import { TOUCH } from "../settings";

/** One short trail in screen coordinates; only keep the latest turning point. */
export class CursorTouch {
  #x = 0;
  #y = 0;
  #dx = 0;
  #dy = 0;
  #turns = 0;
  #start = -Infinity;
  #last = -Infinity;
  #distance = Infinity;
  #inside = false;
  #approaching = false;
  #petAt = -Infinity;
  #reachAt = -Infinity;
  readonly #random: () => number;
  constructor(random = Math.random) {
    this.#random = random;
  }

  feed(x: number, y: number, now: number, box: Rect | null): "pet" | "reach" | null {
    if (!box) {
      this.#inside = false;
      this.#last = -Infinity;
      return null;
    }
    const distance = Math.hypot(
      Math.max(box.x - x, 0, x - box.x - box.w),
      Math.max(box.y - y, 0, y - box.y - box.h),
    );
    const previous = now - this.#last < TOUCH.gapMs ? this.#distance : Infinity;
    if (!Number.isFinite(previous)) this.#approaching = false;
    if (distance > box.w * 0.6) this.#approaching = true;
    this.#distance = distance;
    this.#last = now;
    if (distance > 0) {
      this.#inside = false;
      if (
        previous < Infinity &&
        this.#approaching &&
        distance < box.w * 0.35 &&
        now - this.#reachAt >= TOUCH.reachCooldown
      ) {
        this.#approaching = false;
        this.#reachAt = now;
        if (this.#random() < TOUCH.reachChance) return "reach";
      }
      return null;
    }
    this.#approaching = false;
    if (!this.#inside || previous !== 0 || now - this.#start > TOUCH.windowMs) {
      this.#start = now;
      this.#turns = 0;
      this.#inside = true;
      this.#dx = 0;
      this.#dy = 0;
      this.#x = x;
      this.#y = y;
      return null;
    }
    const dx = x - this.#x,
      dy = y - this.#y;
    if (Math.hypot(dx, dy) < Math.max(5, box.w * 0.055)) return null;
    if (dx * this.#dx + dy * this.#dy < 0) this.#turns++;
    this.#dx = dx;
    this.#dy = dy;
    this.#x = x;
    this.#y = y;
    if (this.#turns < TOUCH.turns || now - this.#petAt < TOUCH.petCooldown) return null;
    this.#inside = false;
    this.#petAt = now;
    return "pet";
  }
}
