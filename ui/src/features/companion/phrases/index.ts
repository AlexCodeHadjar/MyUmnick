/**
 * Выбор фразы поглаживания (BEHAVIOR §7): раздел — по номеру клика в серии и по состоянию спутника,
 * фраза — без повтора последних 12. Чистые функции — проверяются тестами.
 */
import { PET_EN } from "./pet.en";
import { PET_RU } from "./pet.ru";
import type { PetPhrases, WatchPhrases } from "./types";
import { WATCH_EN } from "./watch.en";
import { WATCH_RU } from "./watch.ru";

export type { PetPhrases, WatchPhrases } from "./types";
export { PET_EN, PET_RU, WATCH_EN, WATCH_RU };

export function watchPhrases(lang: string): WatchPhrases {
  return lang === "en" ? WATCH_EN : WATCH_RU;
}

/** Клики серии, на которых спутник отвечает фразой: чаще — надоест. */
const SPOKEN: ReadonlyMap<number, keyof PetPhrases> = new Map([
  [1, "first"],
  [3, "more"],
  [6, "lots"],
  [10, "overload"],
  [15, "max"],
] as const);
const MEMORY = 12;

export interface PetContext {
  /** Номер клика в серии (клики не дальше 3 с друг от друга), с 1. */
  count: number;
  sleeping: boolean;
  singing: boolean;
  /** Недавно трясли мышью (T4). */
  shaken: boolean;
  /** Пользователь недавно вернулся после долгого отсутствия (T7). */
  comeback: boolean;
  hour: number;
}

export function petPhrases(lang: string): PetPhrases {
  return lang === "en" ? PET_EN : PET_RU;
}

/** Раздел для фразы или `null` — на этом клике молчит. Первое касание окрашено состоянием. */
export function petSection(context: PetContext, random: () => number): keyof PetPhrases | null {
  const section = SPOKEN.get(context.count) ?? null;
  if (section !== "first") return section;
  if (context.sleeping) return "sleepy";
  if (context.shaken) return "held";
  if (context.comeback) return "comeback";
  if (context.singing) return "singing";
  const night = context.hour >= 23 || context.hour < 5;
  const morning = context.hour >= 5 && context.hour < 11;
  if ((night || morning) && random() < 0.5) return night ? "night" : "morning";
  return "first";
}

/** Фраза раздела без повтора недавних; `recent` дополняется сказанной. */
export function petLine(list: readonly string[], recent: string[], random: () => number): string {
  const fresh = list.filter((line) => !recent.includes(line));
  const from = fresh.length > 0 ? fresh : list;
  const line = from[Math.floor(random() * from.length)] ?? "";
  recent.push(line);
  if (recent.length > MEMORY) recent.shift();
  return line;
}
