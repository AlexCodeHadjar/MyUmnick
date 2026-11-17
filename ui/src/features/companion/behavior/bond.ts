/**
 * Привязанность спутника к пользователю (COMPANION.md, этап 3): поглаживания, разговоры и проведённое
 * вместе время копятся, а без внимания медленно забываются (половина за неделю). Высокая — тёплые
 * приветствия, низкая — сдержанные. Хранится между запусками. Чистые функции — проверяются тестами.
 */
export interface Bond {
  /** 0…1. */
  level: number;
  /** Когда обновлено, мс эпохи. */
  at: number;
}

export type BondEvent = "pet" | "talk" | "together";
export type BondTone = "warm" | "cool" | "plain";

export const BOND_KEY = "vtuber.companion.bond";
const START = 0.3;
const HALF_LIFE_MS = 7 * 24 * 3_600_000;
const GAIN: Record<BondEvent, number> = { pet: 0.01, talk: 0.006, together: 0.004 };

/** Забывание: без внимания привязанность тает к стартовой с полураспадом в неделю. */
export function settle(bond: Bond, now: number): Bond {
  const k = 0.5 ** (Math.max(0, now - bond.at) / HALF_LIFE_MS);
  return { level: START + (bond.level - START) * k, at: now };
}

/** Событие внимания: чем выше привязанность, тем медленнее она растёт дальше. */
export function grow(bond: Bond, event: BondEvent, now: number): Bond {
  const fresh = settle(bond, now);
  return { level: Math.min(1, fresh.level + GAIN[event] * (1 - fresh.level)), at: now };
}

export function bondTone(bond: Bond): BondTone {
  if (bond.level > 0.65) return "warm";
  if (bond.level < 0.2) return "cool";
  return "plain";
}

export function parseBond(text: string | null, now: number): Bond {
  try {
    const raw: unknown = text === null ? null : JSON.parse(text);
    if (typeof raw !== "object" || raw === null) return { level: START, at: now };
    const map = new Map<string, unknown>(Object.entries(raw));
    const level = map.get("level");
    const at = map.get("at");
    if (typeof level !== "number" || typeof at !== "number" || level < 0 || level > 1) {
      return { level: START, at: now };
    }
    return settle({ level, at }, now);
  } catch {
    return { level: START, at: now };
  }
}
