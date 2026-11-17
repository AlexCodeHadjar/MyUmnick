/**
 * «Жизнь» спутника между выходками (BEHAVIOR §2, §4.4, §5, §6): настроение и его влияние на «мозг»,
 * привычки пользователя, сайты браузера, любимый значок. Здесь выбор фразы; когда говорить — решает
 * `Companion.svelte`. Время — секунды.
 */
import { locale } from "../../../core";
import type { Brain } from "../body";
import {
  AppWatch,
  FAVORITES_KEY,
  isRecycleBin,
  parseFavorites,
  pickIcon,
  type Habit,
} from "./habits";
import {
  drift,
  loadMood,
  nudge,
  pace,
  restTimes,
  saveMood,
  tone,
  type Mood,
  type MoodEvent,
} from "./mood";
import { petLine } from "../phrases";
import { BOND_KEY, bondTone, grow, parseBond, type Bond } from "./bond";
import type { RemarkTopic } from "../senses";
import { browserTopic } from "../senses";

const SAVE_EVERY_S = 30;

export class Life {
  readonly #brain: Brain;
  readonly #storage: Storage | undefined;
  readonly #random: () => number;
  readonly #apps = new AppWatch();
  readonly #recent: string[] = [];
  #mood: Mood;
  #favorites: Map<string, number>;
  #tickAt = 0;
  #bond: Bond;
  #together = 0;
  #savedAt = 0;

  constructor(brain: Brain, storage: Storage | undefined, random: () => number = Math.random) {
    this.#brain = brain;
    this.#storage = storage;
    this.#random = random;
    this.#mood = loadMood(storage, Date.now());
    this.#favorites = parseFavorites(read(storage, FAVORITES_KEY));
    this.#bond = parseBond(read(storage, BOND_KEY), Date.now());
    this.#apply();
  }

  get mood(): Mood {
    return this.#mood;
  }

  event(event: MoodEvent): void {
    this.#mood = nudge(this.#mood, event);
    // Внимание растит привязанность (этап 3): поглаживания и разговоры.
    if (event === "pet" || event === "talk") this.#bond = grow(this.#bond, event, Date.now());
  }

  get bond(): Bond {
    return this.#bond;
  }

  /** Приветствие по привязанности: тёплое или сдержанное; обычная — `null` (общая фраза). */
  greeting(): string | null {
    const tone = bondTone(this.#bond);
    return tone === "plain" ? null : this.#line(locale.t.companion.bond[tone]);
  }

  /** Раз в секунду: течение настроения, «долго в программе». Возвращает фразу или `null`. */
  tick(now: number): string | null {
    if (now < this.#tickAt) return null;
    const dt = this.#tickAt === 0 ? 1 : now - this.#tickAt + 1;
    this.#tickAt = now + 1;
    const context = { hour: new Date().getHours(), idleS: this.#brain.idleSeconds };
    this.#mood = drift(this.#mood, dt, context);
    if (this.#brain.music === "playing") this.event("song");
    // Минута рядом (спутник на экране) — капля привязанности.
    this.#together += dt;
    if (this.#together >= 60) {
      this.#together = 0;
      this.#bond = grow(this.#bond, "together", Date.now());
    }
    this.#apply();
    if (now - this.#savedAt > SAVE_EVERY_S) {
      this.#savedAt = now;
      saveMood(this.#storage, this.#mood, Date.now());
      write(this.#storage, BOND_KEY, JSON.stringify(this.#bond));
    }
    const habit = this.#apps.tick(now);
    return habit === null ? null : this.#habitLine(habit, null);
  }

  /** Сменилась программа: «первый раз за день» (иногда) или «мечешься». */
  focus(topic: RemarkTopic, now: number): string | null {
    const day = new Date().toISOString().slice(0, 10);
    for (const habit of this.#apps.focus(topic, now, day)) {
      if (habit === "first" && this.#random() > 0.6) continue;
      return this.#habitLine(habit, topic);
    }
    return null;
  }

  /** Своя фраза вместо обычного комментария: по настроению, музыке (с танцем) — или `null`. */
  remark(topic: RemarkTopic): string | null {
    const mood = tone(this.#mood);
    const roll = this.#random();
    if (mood !== "mid" && roll < 0.3) return this.#line(locale.t.companion.mood[mood]);
    if (topic === "music" && roll < 0.6) {
      this.#brain.emote("dance", 4);
      return this.#line(locale.t.companion.remarks.music);
    }
    return null;
  }

  /** Про браузер — по названиям вкладок (BEHAVIOR §5); ничего не узнал — `null`. */
  browser(tabs: readonly string[]): string | null {
    const topic = browserTopic(tabs, this.#random);
    return topic === null ? null : this.#line(locale.t.companion.sites[topic]);
  }

  /** Значок для прыжка: любимые — чаще. */
  icon<T extends { name: string }>(icons: readonly T[]): T | undefined {
    return pickIcon(icons, this.#favorites, this.#random);
  }

  /** Сел на значок: корзина, любимый, пересчёт — или `null` (тогда обычная фраза). */
  iconLine(name: string, count: number): string | null {
    const fun = locale.t.companion.desktopFun;
    if (isRecycleBin(name)) return this.#line(fun.recycle);
    const roll = this.#random();
    if ((this.#favorites.get(name) ?? 0) >= 5 && roll < 0.4) return fun.favorite(name);
    if (count >= 3 && roll > 0.9) return fun.count(count);
    return null;
  }

  /** Погладили, сидя на значке: он становится любимее. */
  petOn(name: string): void {
    this.#favorites.set(name, (this.#favorites.get(name) ?? 0) + 1);
    try {
      this.#storage?.setItem(FAVORITES_KEY, JSON.stringify(Object.fromEntries(this.#favorites)));
    } catch {
      // Не запомнится — любимый значок забудется к перезапуску.
    }
  }

  #habitLine(habit: Habit, topic: RemarkTopic | null): string | null {
    const habits = locale.t.companion.habits;
    if (habit !== "first") return this.#line(habits[habit]);
    const first = new Map<string, readonly string[]>(Object.entries(habits.first));
    const list = topic === null ? undefined : first.get(topic);
    return list === undefined ? null : this.#line(list);
  }

  #apply(): void {
    const times = restTimes(this.#mood);
    this.#brain.layAfter = times.lay;
    this.#brain.sleepAfter = times.sleep;
    this.#brain.pace = pace(this.#mood);
  }

  #line(list: readonly string[]): string {
    return petLine(list, this.#recent, this.#random);
  }
}

function read(storage: Storage | undefined, key: string): string | null {
  try {
    return storage?.getItem(key) ?? null;
  } catch {
    return null;
  }
}

function write(storage: Storage | undefined, key: string, value: string): void {
  try {
    storage?.setItem(key, value);
  } catch {
    // Не запомнится — привязанность начнётся заново.
  }
}
