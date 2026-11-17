/**
 * Настроение спутника (BEHAVIOR §2): бодрость и радость 0…1. Меняются медленно, определяют, когда он
 * ложится и засыпает, как часто гуляет и какие фразы выбирает. Хранится между запусками, за ночь
 * возвращается к среднему. Чистые функции — проверяются тестами.
 */
export interface Mood {
  energy: number;
  joy: number;
  /** Когда сохранено, мс эпохи. */
  at: number;
}

export type MoodEvent = "pet" | "shake" | "comeback" | "talk" | "song";
export type MoodTone = "low" | "mid" | "high";

export const MOOD_KEY = "vtuber.companion.mood";
const MIDDLE = 0.6;
/** За столько часов без запуска настроение полностью возвращается к среднему. */
const RESET_H = 8;

const NUDGE: Record<MoodEvent, { energy: number; joy: number }> = {
  pet: { energy: 0.02, joy: 0.05 },
  shake: { energy: 0.05, joy: -0.15 },
  comeback: { energy: 0.1, joy: 0.12 },
  talk: { energy: 0.01, joy: 0.03 },
  song: { energy: 0.002, joy: 0.004 },
};

function clamp(value: number): number {
  return Math.min(1, Math.max(0, value));
}

export function neutralMood(now: number): Mood {
  return { energy: MIDDLE, joy: MIDDLE, at: now };
}

/** Событие сдвигает настроение. */
export function nudge(mood: Mood, event: MoodEvent): Mood {
  const step = NUDGE[event];
  return { ...mood, energy: clamp(mood.energy + step.energy), joy: clamp(mood.joy + step.joy) };
}

/**
 * Течение времени (`dt` секунд): ночью бодрость падает, утром растёт; долгий простой тянет радость вниз,
 * иначе она медленно возвращается к середине.
 */
export function drift(mood: Mood, dt: number, context: { hour: number; idleS: number }): Mood {
  const minutes = dt / 60;
  const night = context.hour >= 23 || context.hour < 6;
  const morning = context.hour >= 6 && context.hour < 11;
  const energy = mood.energy + (night ? -0.02 : morning ? 0.01 : 0) * minutes;
  const toward = context.idleS > 600 ? 0.3 : MIDDLE;
  const joy = mood.joy + (toward - mood.joy) * Math.min(1, 0.01 * minutes);
  return { ...mood, energy: clamp(energy), joy: clamp(joy) };
}

export function tone(mood: Mood): MoodTone {
  const level = (mood.energy + mood.joy) / 2;
  return mood.joy < 0.3 ? "low" : level > 0.8 ? "high" : "mid";
}

/** Через сколько секунд простоя ложится и засыпает: устал — раньше. */
export function restTimes(mood: Mood): { lay: number; sleep: number } {
  if (mood.energy < 0.25) return { lay: 45, sleep: 150 };
  if (mood.energy > 0.8) return { lay: 150, sleep: 420 };
  return { lay: 90, sleep: 300 };
}

/** Множитель пауз между прогулками: бодрый гуляет чаще. */
export function pace(mood: Mood): number {
  return 1.6 - mood.energy;
}

/** Сохранённое настроение; за ночь (8 ч) — к середине. */
export function parseMood(text: string | null, now: number): Mood {
  let raw: unknown;
  try {
    raw = text === null ? null : JSON.parse(text);
  } catch {
    raw = null;
  }
  if (typeof raw !== "object" || raw === null) return neutralMood(now);
  const map = new Map<string, unknown>(Object.entries(raw));
  const energy = map.get("energy");
  const joy = map.get("joy");
  const at = map.get("at");
  if (typeof energy !== "number" || typeof joy !== "number" || typeof at !== "number") {
    return neutralMood(now);
  }
  const k = Math.min(1, Math.max(0, (now - at) / 3_600_000 / RESET_H));
  return {
    energy: clamp(energy + (MIDDLE - energy) * k),
    joy: clamp(joy + (MIDDLE - joy) * k),
    at: now,
  };
}

export function loadMood(storage: Storage | undefined, now: number): Mood {
  try {
    return parseMood(storage?.getItem(MOOD_KEY) ?? null, now);
  } catch {
    return neutralMood(now);
  }
}

export function saveMood(storage: Storage | undefined, mood: Mood, now: number): void {
  try {
    storage?.setItem(MOOD_KEY, JSON.stringify({ ...mood, at: now }));
  } catch {
    // Не запомнится — настроение начнётся со среднего.
  }
}
