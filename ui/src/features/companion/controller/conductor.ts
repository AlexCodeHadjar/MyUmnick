/**
 * Исполнитель решений «Разума» (MIND §4): что значит каждое действие для тела и голоса — пойти к окну,
 * сказать фразу, потыкать, прыгнуть по значкам, погулять, сесть смотреть фильм или тихо в угол.
 * Решает, ЧТО делать, `Mind`; здесь — КАК.
 */
import { locale } from "../../../core";
import type { Life } from "../behavior";
import type { Brain } from "../body";
import type { ActivityId, Mind, Senses, VoiceKind } from "../mind";
import { watchPhrases } from "../phrases";
import { choosePoke, remark } from "../senses";
import { floorSpot, followSpot, hostOf, snap } from "../space";
import type { Presence } from "./presence";
import type { Scout } from "./scout";

/** Предложить фразу голосу; `watchLine` — фраза самого просмотра (пропускается и во время фильма). */
export type Speak = (text: string, kind: VoiceKind, watchLine?: boolean) => void;

export interface ConductorParts {
  brain: Brain;
  mind: Mind;
  life: Life;
  scout: Scout;
  presence: Presence;
}

/** Что от контроллера нужно для картины кадра. */
export interface Situation {
  listening: boolean;
  holding: boolean;
  behavior: Senses["behavior"];
  calm: boolean;
  userBusy: boolean;
  lastLine: string;
}

const POKE_BACK_MS = 5200;

function pickOne(list: readonly string[]): string {
  return list[Math.floor(Math.random() * list.length)] ?? "";
}

export class Conductor {
  readonly #p: ConductorParts;
  readonly #speak: Speak;
  /** Фраза о программе (привычка дня, «мечешься») для ближайшего «поговорить». */
  topicLine: string | null = null;
  poking = false;
  #cornerPending = false;
  #watchLineAt = 0;
  #lastPhase = "hidden";
  #lastLine = "";
  #watchSince = 0;

  constructor(parts: ConductorParts, speak: Speak) {
    this.#p = parts;
    this.#speak = speak;
  }

  /** Раз в кадр: решение «Разума», режимы в углу, пауза «осмотреться». */
  update(now: number, situation: Situation): void {
    const { brain, mind } = this.#p;
    this.#lastLine = situation.lastLine;
    const choice = mind.update(now / 1000, this.#senses(now, situation));
    if (choice !== null) this.#act(choice.id, choice.previous, now);
    if (this.#cornerPending && brain.phase === "rest" && !situation.holding) {
      this.#cornerPending = false;
      const corner = floorSpot(brain.surfaceList, true);
      if (corner !== null) brain.goTo(corner);
    }
    if (brain.watching && now >= this.#watchLineAt) {
      this.#watchLineAt = now + (480 + Math.random() * 360) * 1000;
      this.#speak(pickOne(watchPhrases(locale.lang).during), "ambient", true);
    }
    // Дошёл, допрыгнул, долез — 2–4 с «осматривается» (MIND §3.4).
    if (brain.phase === "rest" && this.#lastPhase !== "rest" && this.#lastPhase !== "hidden") {
      mind.settle(now / 1000, 2 + Math.random() * 2);
    }
    this.#lastPhase = brain.phase;
  }

  #senses(now: number, situation: Situation): Senses {
    const { brain, presence, scout, life } = this.#p;
    const shown = presence.shown;
    const raw = scout.video(now, presence.world?.fullscreen ?? false);
    return {
      resting: shown && brain.phase === "rest" && !situation.holding && !this.poking,
      listening: situation.listening,
      singing: shown && brain.music === "playing",
      video: shown && raw.video,
      fullscreen: shown && raw.fullscreen,
      desktop: scout.desktop,
      behavior: situation.behavior,
      energy: life.mood.energy,
      userBusy: situation.userBusy,
      hour: new Date().getHours(),
      calm: situation.calm || brain.watching,
    };
  }

  #act(id: ActivityId, previous: string, now: number): void {
    this.#leave(previous);
    if (id === "watch" || id === "hush") this.#enterCorner(id, now);
    else if (id === "follow") this.#follow();
    else if (id === "chat") void this.#chat();
    else if (id === "poke") void this.poke();
    else if (id === "hop") void this.#hop();
    else if (id === "wander") this.#p.brain.stroll();
    else if (id === "play") this.#play();
  }

  /** Выйти из режима: досмотрели — реплика и домой к активному окну. */
  #leave(previous: string): void {
    const { brain } = this.#p;
    if (previous === "watch") {
      brain.watching = false;
      if (performance.now() - this.#watchSince > 60_000) {
        this.#speak(pickOne(watchPhrases(locale.lang).end), "reaction", true);
      }
    }
    if (previous === "hush") {
      brain.quiet = false;
      // Вышли из полного экрана (T14) — по сглаженному факту «Разума», а не по миганию сигнала.
      this.#speak(pickOne(locale.t.companion.triggers.back), "reaction");
    }
    if (previous === "watch" || previous === "hush") this.#follow(true);
  }

  #enterCorner(id: "watch" | "hush", now: number): void {
    const { brain } = this.#p;
    brain.watching = id === "watch";
    brain.quiet = id === "hush";
    this.#watchSince = now;
    // Полный экран без видео (этап 6): не сидит в углу, а выглядывает из-за правого края экрана.
    const screen = this.#p.presence.world?.monitor;
    if (id === "hush" && screen !== undefined) {
      brain.visit(screen.x + screen.w, screen.y + screen.h * 0.62, "peek", -1);
    } else {
      this.#cornerPending = true;
    }
    // Первая тихая реплика — через 4–7 мин, дальше реже (BEHAVIOR §11.2).
    this.#watchLineAt = now + (240 + Math.random() * 180) * 1000;
    if (id === "watch") this.#speak(pickOne(watchPhrases(locale.lang).start), "reaction", true);
    else if (Math.random() < 0.5) this.#speak(pickOne(locale.t.companion.watch.quiet), "reaction");
  }

  /** Игра: бежит за курсором с репликой. */
  #play(): void {
    const { brain } = this.#p;
    if (brain.cursorX !== null) brain.chase(brain.cursorX);
    this.#speak(pickOne(locale.t.companion.triggers.play), "reaction");
  }

  /** К активному окну; `always` — даже если уже на нём (вернуться из угла). */
  #follow(always = false): void {
    const { brain, presence } = this.#p;
    const world = presence.world;
    if (world === null) return;
    const spot = followSpot(world, brain.surfaceList, world.focus);
    if (spot !== null && (always || hostOf(spot) !== hostOf(brain.spot))) brain.goTo(spot);
  }

  /** «Поговорить»: фраза о программе, привычке, сайте или по настроению. */
  async #chat(): Promise<void> {
    const { life, scout, brain } = this.#p;
    const ready = this.topicLine ?? life.remark(scout.topic);
    this.topicLine = null;
    if (ready !== null) {
      this.#speak(ready, "ambient");
      return;
    }
    const line = scout.topic === "browser" ? life.browser(await scout.tabs()) : null;
    const hour = new Date().getHours();
    const context = { topic: scout.topic, hour, idleS: brain.idleSeconds };
    this.#speak(line ?? remark(locale.t, context, Math.random, this.#lastLine), "ambient");
  }

  /** Подлететь к видимому элементу экрана, ткнуть, назвать его и вернуться. Нечего — фраза. */
  async poke(): Promise<void> {
    const { brain, presence, scout } = this.#p;
    const world = presence.world;
    if (world === null) return;
    this.poking = true;
    const near = choosePoke(await scout.targets(), world.monitor);
    if (near === null || brain.phase !== "rest" || !presence.shown) {
      this.poking = false;
      const context = { topic: scout.topic, hour: new Date().getHours(), idleS: brain.idleSeconds };
      this.#speak(remark(locale.t, context, Math.random, this.#lastLine), "ambient");
      return;
    }
    const back = brain.spot;
    brain.visit(near.x, near.y, "poke", near.facing);
    this.#speak(pickOne(locale.t.companion.poke.map((line) => line(near.name))), "reaction");
    setTimeout(() => {
      this.poking = false;
      if (brain.phase !== "rest") return;
      const home = back ?? followSpot(world, brain.surfaceList, { kind: "desktop" });
      if (home !== null) brain.goTo(home);
    }, POKE_BACK_MS);
  }

  /** «Прыжок по значкам»: на любимый значок с репликой или ткнуть в значок. */
  async #hop(): Promise<void> {
    const { brain, scout, life } = this.#p;
    await scout.refreshIcons();
    const chosen = life.icon(scout.icons);
    if (chosen === undefined || brain.phase !== "rest") return;
    if (Math.random() < 0.4) {
      void this.poke();
      return;
    }
    const spot = snap(brain.surfaceList, chosen.rect.x + chosen.rect.w / 2, chosen.rect.y + 6, 30);
    if (spot === null) return;
    brain.goTo(spot);
    const perch = pickOne(locale.t.companion.perch.map((line) => line(chosen.name)));
    this.#speak(life.iconLine(chosen.name, scout.icons.length) ?? perch, "reaction");
  }
}
