/**
 * Игра с курсором (COMPANION.md, этап 4): пользователь быстро кружит мышью рядом со спутником — это
 * приглашение поиграть. Распознаёт «кружение»: за последние 1,5 с курсор прошёл длинный путь, но остался
 * рядом с персонажем (не просто пролетел мимо). Чистый класс — проверяется тестами.
 */
const WINDOW_MS = 1500;
const NEAR_PX = 320;
const PATH_PX = 1400;
const DRIFT_PX = 380;
/** Ближе этого к груди — «поймал». */
const CATCH_PX = 45;

interface Point {
  x: number;
  y: number;
  t: number;
}

export class PlayWatch {
  #trail: Point[] = [];

  /** Курсор в момент `t` (мс); `chest` — грудь персонажа или `null`. Вернёт `true`, если с ним играют. */
  feed(x: number, y: number, t: number, chest: { x: number; y: number } | null): boolean {
    this.#trail = [...this.#trail.filter((p) => t - p.t < WINDOW_MS), { x, y, t }];
    if (chest === null || this.#trail.length < 6) return false;
    const near = this.#trail.every((p) => Math.hypot(p.x - chest.x, p.y - chest.y) < NEAR_PX);
    let path = 0;
    for (let i = 1; i < this.#trail.length; i += 1) {
      const a = this.#trail[i - 1];
      const b = this.#trail[i];
      if (a !== undefined && b !== undefined) path += Math.hypot(b.x - a.x, b.y - a.y);
    }
    const first = this.#trail[0];
    const drift = first === undefined ? 0 : Math.hypot(x - first.x, y - first.y);
    return near && path > PATH_PX && drift < DRIFT_PX;
  }
}

/** Курсор у самой груди — «поймал». */
export function caught(x: number, y: number, chest: { x: number; y: number }): boolean {
  return Math.hypot(x - chest.x, y - chest.y) < CATCH_PX;
}
