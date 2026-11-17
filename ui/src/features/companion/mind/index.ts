/**
 * «Разум» спутника (MIND.md, ADR-0051): картина мира со сглаживанием, потребности, стимулы, арбитр
 * действий и голос — одно место, где решается, что он делает. `Companion.svelte` только сообщает, что
 * видит, и исполняет выбранное действие.
 */
import { ACTIVITIES, type ActivityId, type MindContext } from "./activities";
import { Arbiter, type Choice } from "./arbiter";
import { Drives, type Drive } from "./drives";
import { Fact } from "./fact";
import { Stimuli, type Stimulus } from "./stimuli";
import { Voice } from "./voice";

export type { ActivityId } from "./activities";
export type { VoiceKind } from "./voice";

const DECIDE_EVERY_S = 0.5;

/** Сырые наблюдения кадра: сглаживает их сам «Разум». */
export interface Senses {
  resting: boolean;
  listening: boolean;
  singing: boolean;
  video: boolean;
  fullscreen: boolean;
  desktop: boolean;
  behavior: "follow" | "stay" | "wander";
  energy: number;
  userBusy: boolean;
  hour: number;
}

/** Что утоляет каждое действие, когда начинается. */
const SATISFIES: Partial<Record<ActivityId, readonly [Drive, number]>> = {
  chat: ["social", 0.7],
  poke: ["curiosity", 0.7],
  hop: ["curiosity", 0.5],
  wander: ["restless", 0.8],
};

function isActivity(id: string): id is ActivityId {
  return ACTIVITIES.some((one) => one.id === id);
}

export class Mind {
  readonly voice = new Voice();
  readonly drives = new Drives();
  readonly #stimuli = new Stimuli();
  readonly #arbiter: Arbiter<MindContext>;
  // Сглаживание (MIND §3.1): видео — 2 с на «началось», 4 с на «кончилось».
  readonly #video = new Fact(2, 4);
  readonly #fullscreen = new Fact(1, 3);
  readonly #desktop = new Fact(1.5, 1);
  #decideAt = -Infinity;
  #last: number | null = null;

  constructor(random: () => number = Math.random) {
    this.#arbiter = new Arbiter(ACTIVITIES, random);
  }

  get activity(): ActivityId {
    const id = this.#arbiter.current;
    return isActivity(id) ? id : "idle";
  }

  get desktop(): boolean {
    return this.#desktop.value;
  }

  /** Событие (MIND §3.3): поднимает оценки подходящих действий; решение — со следующего кадра. */
  feel(kind: Stimulus, now: number, strength = 1, lifeS = 20): void {
    this.#stimuli.add(kind, now, strength, lifeS);
    // Решение — через 0,3 с: быстрый Alt+Tab туда-обратно не уводит к окну.
    this.#decideAt = Math.min(this.#decideAt, now + 0.3);
  }

  /** Дошёл до места — пауза «осмотреться» (MIND §3.4, правило 7). */
  settle(now: number, seconds: number): void {
    this.#arbiter.settle(now, seconds);
  }

  satisfy(drive: Drive, amount: number): void {
    this.drives.satisfy(drive, amount);
  }

  /** Раз в кадр. Вернёт выбор, если действие сменилось, иначе `null`. */
  update(now: number, senses: Senses): (Choice & { id: ActivityId }) | null {
    const dt = this.#last === null ? 0 : Math.min(1, now - this.#last);
    this.#last = now;
    const video = this.#video.update(senses.video, now);
    const fullscreen = this.#fullscreen.update(senses.fullscreen, now);
    this.#desktop.update(senses.desktop, now);
    const night = senses.hour >= 23 || senses.hour < 6;
    this.drives.tick(dt, { energy: senses.energy, userBusy: senses.userBusy, night });
    if (now < this.#decideAt) return null;
    this.#decideAt = now + DECIDE_EVERY_S;
    const context: MindContext = {
      resting: senses.resting,
      listening: senses.listening,
      singing: senses.singing,
      video,
      hush: fullscreen && !video,
      desktop: this.#desktop.value,
      behavior: senses.behavior,
      energy: senses.energy,
      social: this.drives.get("social"),
      curiosity: this.drives.get("curiosity"),
      restless: this.drives.get("restless"),
      focus: this.#stimuli.level("focus", now),
      canChat: this.voice.canChat(now),
    };
    const choice = this.#arbiter.choose(context, now);
    if (!choice.changed || !isActivity(choice.id)) return null;
    this.#enter(choice.id);
    return { ...choice, id: choice.id };
  }

  #enter(id: ActivityId): void {
    const satisfies = SATISFIES[id];
    if (satisfies !== undefined) this.drives.satisfy(...satisfies);
    if (id === "follow" || id === "chat") this.#stimuli.consume("focus");
  }
}
