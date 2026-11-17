/**
 * Привычки пользователя глазами спутника (BEHAVIOR §4.4, §6): первая встреча с программой за день,
 * долгая работа в одной программе, частые переключения, любимый значок. Только имя программы и
 * названия значков — то, что спутник и так видит. Чистые классы — проверяются тестами.
 */
import type { RemarkTopic } from "./remarks";

export type Habit = "first" | "long" | "switching";

/** Темы, у которых есть «первый раз за день»: «прочее» и рабочий стол — без него. */
const DAILY: ReadonlySet<RemarkTopic> = new Set([
  "browser",
  "code",
  "chat",
  "music",
  "video",
  "game",
  "office",
  "terminal",
  "files",
]);
const LONG_S = 40 * 60;
const SWITCHES = 8;

export class AppWatch {
  #day = "";
  #seen = new Set<RemarkTopic>();
  #topic: RemarkTopic | null = null;
  #since = 0;
  #toldLong = false;
  #switches: number[] = [];

  /** Активной стала программа темы `topic` в момент `now` (с); `day` — дата `YYYY-MM-DD`. */
  focus(topic: RemarkTopic, now: number, day: string): Habit[] {
    if (day !== this.#day) {
      this.#day = day;
      this.#seen = new Set();
    }
    if (topic === this.#topic) return [];
    this.#topic = topic;
    this.#since = now;
    this.#toldLong = false;
    this.#switches = [...this.#switches.filter((t) => now - t < 60), now];
    const out: Habit[] = [];
    if (DAILY.has(topic) && !this.#seen.has(topic)) out.push("first");
    this.#seen.add(topic);
    if (this.#switches.length > SWITCHES) {
      out.push("switching");
      this.#switches = [];
    }
    return out;
  }

  /** Сидит в одной программе 40 мин — один раз за заход. */
  tick(now: number): Habit | null {
    if (this.#topic === null || this.#toldLong || !DAILY.has(this.#topic)) return null;
    if (now - this.#since < LONG_S) return null;
    this.#toldLong = true;
    return "long";
  }

  get topic(): RemarkTopic | null {
    return this.#topic;
  }
}

export const FAVORITES_KEY = "vtuber.companion.favorites";

/** Значок, на который садиться: чаще тот, где чаще гладили (вес 1 + число поглаживаний). */
export function pickIcon<T extends { name: string }>(
  icons: readonly T[],
  favorites: ReadonlyMap<string, number>,
  random: () => number,
): T | undefined {
  const weights = icons.map((one) => 1 + Math.min(20, favorites.get(one.name) ?? 0));
  let roll = random() * weights.reduce((sum, w) => sum + w, 0);
  for (const [i, icon] of icons.entries()) {
    roll -= weights[i] ?? 1;
    if (roll < 0) return icon;
  }
  return icons.at(-1);
}

export function isRecycleBin(name: string): boolean {
  return /корзин|recycle|trash/i.test(name);
}

export function parseFavorites(text: string | null): Map<string, number> {
  try {
    const raw: unknown = text === null ? null : JSON.parse(text);
    if (typeof raw !== "object" || raw === null) return new Map();
    return new Map(
      Object.entries(raw).filter(
        (entry): entry is [string, number] => typeof entry[1] === "number" && entry[1] > 0,
      ),
    );
  } catch {
    return new Map();
  }
}
