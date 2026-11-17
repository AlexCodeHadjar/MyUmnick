/**
 * Реакции спутника на триггеры (BEHAVIOR §3, §7): фраза в облачке и короткая поза-эмоция. Распознавание —
 * `triggers.ts`, фразы поглаживания — `phrases/`, тексты триггеров — словари (`companion.triggers`).
 * Время — секунды (`performance.now() / 1000`).
 */
import { locale } from "../../core";
import type { Brain } from "./brain";
import type { MoodEvent } from "./mood";
import { petLine, petPhrases, petSection } from "./phrases";
import { timeOfDay } from "./remarks";
import { Cooldowns, CursorWatch, dragged, lateNight, shaken, type Trigger } from "./triggers";

/** Серия поглаживаний: клики не дальше 3 с друг от друга. */
const PET_SERIES_S = 3;
/** После тряски / возвращения гладят «по-особому» столько секунд. */
const AFTER_S = 30;

type Say = (text: string) => void;

export class Reactions {
  readonly #brain: Brain;
  readonly #say: Say;
  readonly #random: () => number;
  /** Настроение слышит тряску, возвращение и поглаживания (`life.ts`, BEHAVIOR §2). */
  onMood: (event: MoodEvent) => void = () => undefined;
  readonly #cool = new Cooldowns();
  readonly #cursor = new CursorWatch();
  readonly #recent: string[] = [];
  #pets: number[] = [];
  #shook: { x: number; y: number; t: number }[] = [];
  #shakenAt = -Infinity;
  #comebackAt = -Infinity;
  #dizzyPending = false;
  #host: { x: number; y: number; t: number } | null = null;
  #nightCheck = 0;

  constructor(brain: Brain, say: Say, random: () => number = Math.random) {
    this.#brain = brain;
    this.#say = say;
    this.#random = random;
  }

  /** Сработать с перезарядкой: фраза из словаря; `false` — ещё рано. */
  fire(kind: Exclude<Trigger, "greet">, now: number): boolean {
    if (!this.#cool.ready(kind, now)) return false;
    this.#speak(locale.t.companion.triggers[kind]);
    return true;
  }

  /** Спутник появился (T6): приветствие по времени суток и взмах рукой. */
  greet(now: number): void {
    if (!this.#cool.ready("greet", now)) return;
    this.#speak(locale.t.companion.triggers.greet[timeOfDay(new Date().getHours())]);
    this.#brain.emote("wave", 2);
  }

  /** Курсор сдвинулся или стоит (`frame` зовёт и без движения — для T8). */
  cursor(x: number, y: number, now: number, visible: boolean): void {
    const brain = this.#brain;
    const body =
      visible && brain.phase === "rest" ? { x: brain.x, y: brain.y - brain.chest } : null;
    for (const kind of this.#cursor.feed(x, y, now, body)) {
      if (kind === "greet" || !this.fire(kind, now)) continue;
      if (kind === "comeback") {
        this.#comebackAt = now;
        this.onMood("comeback");
        brain.wake();
        brain.emote("wave", 2);
      } else if (kind === "stare") {
        brain.emote("wave", 1.5);
      }
    }
  }

  /** Держат мышью: трясут — «голова кружится» (T4), после приземления — поза `dizzy`. */
  held(x: number, y: number, now: number): void {
    const t = now * 1000;
    this.#shook = [...this.#shook.filter((p) => t - p.t < 1000), { x, y, t }];
    if (!shaken(this.#shook) || !this.fire("dizzy", now)) return;
    this.#shakenAt = now;
    this.#dizzyPending = true;
    this.onMood("shake");
  }

  /** Отпустили: бросили с размаху (T5). */
  released(speed: number, now: number): void {
    this.#shook = [];
    if (speed > 1800) this.fire("toss", now);
  }

  /** Окно-хозяин сдвинулось или пропало (T10, T11). */
  host(rect: { x: number; y: number } | null, now: number): void {
    const before = this.#host;
    if (rect === null) {
      if (before !== null) this.fire("homeless", now);
      this.#host = null;
      return;
    }
    if (before !== null && dragged(before, rect, now - before.t)) this.fire("drag", now);
    this.#host = { ...rect, t: now };
  }

  /** Погладили (T3): фраза по номеру клика в серии и состоянию; на остальных кликах молчит. */
  pet(now: number): void {
    this.#pets = [...this.#pets.filter((t) => now - t < PET_SERIES_S), now];
    this.onMood("pet");
    const brain = this.#brain;
    const section = petSection(
      {
        count: this.#pets.length,
        sleeping: brain.drowsy,
        singing: brain.music === "playing",
        shaken: now - this.#shakenAt < AFTER_S,
        comeback: now - this.#comebackAt < AFTER_S,
        hour: new Date().getHours(),
      },
      this.#random,
    );
    if (section !== null)
      this.#say(petLine(petPhrases(locale.lang)[section], this.#recent, this.#random));
  }

  /** Раз в кадр: отложенная «кружится», ночь (T16) — раз в минуту проверка часа. */
  tick(now: number): void {
    const brain = this.#brain;
    if (this.#dizzyPending && brain.phase === "rest") {
      this.#dizzyPending = false;
      brain.emote("dizzy", 2.5);
    }
    if (now < this.#nightCheck) return;
    this.#nightCheck = now + 60;
    if (brain.phase === "rest" && lateNight(new Date().getHours()) && this.fire("night", now)) {
      brain.emote("yawn", 2.5);
    }
  }

  /** Начал лезть по стене — иногда комментирует. */
  climbing(): void {
    if (this.#random() < 0.4) this.#speak(locale.t.companion.triggers.climb);
  }

  #speak(list: readonly string[]): void {
    const line = petLine(list, this.#recent, this.#random);
    if (line !== "") this.#say(line);
  }
}
