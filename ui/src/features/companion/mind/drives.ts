/**
 * Потребности спутника (MIND §3.2, по образцу The Sims): растут сами и утоляются действиями. Желание
 * поговорить или погулять копится, а не срабатывает по таймеру.
 */
import { clamp01 } from "./curves";

export type Drive = "social" | "curiosity" | "restless";

/** Секунд от нуля до полной при обычных условиях. */
const FILL_S: Record<Drive, number> = { social: 300, curiosity: 360, restless: 120 };

export interface DriveContext {
  /** Бодрость 0…1 (настроение). */
  energy: number;
  /** Пользователь активно работает (мышь двигалась за последнюю минуту). */
  userBusy: boolean;
  night: boolean;
}

export class Drives {
  readonly #level: Record<Drive, number>;

  constructor(start: Partial<Record<Drive, number>> = {}) {
    this.#level = { social: 0.3, curiosity: 0.3, restless: 0.3, ...start };
  }

  get(drive: Drive): number {
    return this.#level[drive];
  }

  tick(dt: number, context: DriveContext): void {
    // Ночью и уставшим — всё медленнее: затихает сам, без отдельного правила.
    const calm = (context.night ? 0.4 : 1) * (0.5 + context.energy * 0.5);
    const rates: Record<Drive, number> = {
      social: context.userBusy ? 0.5 : 1,
      curiosity: 1,
      restless: context.energy * 1.4,
    };
    for (const drive of ["social", "curiosity", "restless"] as const) {
      this.#level[drive] = clamp01(this.#level[drive] + (dt / FILL_S[drive]) * rates[drive] * calm);
    }
  }

  satisfy(drive: Drive, amount: number): void {
    this.#level[drive] = clamp01(this.#level[drive] - amount);
  }
}
