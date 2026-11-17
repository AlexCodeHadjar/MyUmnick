/**
 * Контроллер спутника: собирает тело, «Разум», жизнь, реакции, органы чувств, присутствие и жесты и
 * отвечает на события оболочки и главного окна. Вид (`Companion.svelte`) только передаёт события и
 * рисует то, что здесь решено. Порты оболочки — через конструктор (тест подставит подделку).
 */
import { isLang, locale } from "../../../core";
import { EMOTION_HUE } from "../../avatar/orb/palette";
import type { RadioFeed, RadioMode } from "../../radio";
import { Life, Reactions } from "../behavior";
import { Brain } from "../body";
import { CANVAS_RATIO, type CompanionStage, type Look } from "../look";
import { Mind, Sanity, type Fix, type VoiceKind } from "../mind";
import { watchPhrases } from "../phrases";
import { caught, PlayWatch } from "../senses";
import { hostOf, ICONS, type Pose, type Rect, type World } from "../space";
import { shouldShow, type CompanionSettings } from "../settings";
import { Conductor } from "./conductor";
import { Gestures } from "./gestures";
import type { Ports } from "./ports";
import { Presence, type MainState } from "./presence";
import { Scout } from "./scout";
import { Speech } from "./speech";

/** Подача главного окна (`companion-feed`, ADR-0045, ADR-0049). */
export interface Feed {
  mouth: number;
  speaking: boolean;
  emotion: string;
  text: string;
  lang: string;
  radio?: RadioFeed;
}

const GREET_DELAY_MS = 900;
/** Эмоция → короткая поза тела и её длительность (с); кадры уже есть (FRAMES-2). */
const EMOTION_POSE: ReadonlyMap<string, readonly [Pose, number]> = new Map([
  ["happy", ["wave", 1.6]],
  ["embarrassed", ["wave", 1.2]],
  ["sad", ["sit_corner", 3]],
  ["surprised", ["float", 0.8]],
] as const);
const CURSOR_FEED_MS = 250;
const BUSY_MS = 60_000;

function pickOne(list: readonly string[]): string {
  return list[Math.floor(Math.random() * list.length)] ?? "";
}

export class CompanionController {
  readonly brain = new Brain();
  readonly mind = new Mind();
  readonly speech = new Speech();
  /** Сторож: не даёт телу и «Разуму» «сойти с ума» (COMPANION.md, часть III). */
  readonly sanity = new Sanity();
  readonly look: Look = {
    mouth: 0,
    speaking: false,
    hue: EMOTION_HUE.neutral,
    attention: 0,
    panel: null,
  };
  readonly life: Life;
  readonly reactions: Reactions;
  readonly presence: Presence;
  readonly scout: Scout;
  readonly gestures: Gestures;
  readonly conductor: Conductor;
  settings: CompanionSettings;
  radio: RadioFeed | null = null;
  stage: CompanionStage | null = null;
  readonly #ports: Ports;
  #assistant = false;
  #cursor: { x: number; y: number } | null = null;
  #cursorFedAt = 0;
  #movedAt = 0;
  #lastFocus = "";
  #attached: number | null = null;
  #lastHit = "";
  #lastPhase = "hidden";
  #emotion = "neutral";
  readonly #play = new PlayWatch();
  #caughtAt = 0;

  constructor(ports: Ports, storage: Storage, settings: CompanionSettings) {
    this.#ports = ports;
    this.settings = settings;
    const brain = this.brain;
    this.life = new Life(brain, storage);
    this.reactions = new Reactions(brain, (text, kind) => {
      this.speak(text, kind);
    });
    this.reactions.onMood = (event) => {
      this.life.event(event);
    };
    this.presence = new Presence(ports, brain);
    this.scout = new Scout(ports, brain, (rect) => this.presence.toCss(rect));
    this.gestures = new Gestures(brain, {
      pet: (now) => {
        this.pet(now);
      },
      held: (x, y, now) => {
        this.reactions.held(x, y, now / 1000);
      },
      released: (speed, now) => {
        this.reactions.released(speed, now / 1000);
      },
    });
    const parts = {
      brain,
      mind: this.mind,
      life: this.life,
      scout: this.scout,
      presence: this.presence,
    };
    this.conductor = new Conductor(parts, (text, kind, watchLine) => {
      this.speak(text, kind, watchLine);
    });
    this.#applyBehavior();
  }

  /**
   * Предложить фразу голосу «Разума» (MIND §3.5). Смотрим фильм — только ответы на действия
   * пользователя и фразы самого просмотра: ни тычков, ни реакций на мышь (ADR-0052).
   */
  speak(text: string, kind: VoiceKind, watchLine = false): void {
    if (text === "" || (this.brain.watching && kind !== "direct" && !watchLine)) return;
    this.mind.voice.offer(text, kind, performance.now() / 1000);
  }

  setSettings(next: CompanionSettings): void {
    this.settings = next;
    this.refresh();
  }

  refresh(): void {
    this.#applyBehavior();
    void this.presence.show(shouldShow(this.settings, this.presence.mainShown)).then((arrived) => {
      // Вышел из портала — поздоровался (T6).
      if (arrived)
        setTimeout(() => {
          this.#greet();
        }, GREET_DELAY_MS);
    });
  }

  onWorld(raw: World): void {
    const presence = this.presence;
    if (presence.setWorld(raw) && presence.shown && !this.gestures.active) presence.moveToMonitor();
    this.refresh();
    // Показали раньше, чем пришла картина окон: выйти сейчас (иначе персонаж так и не появлялся).
    if (presence.shown && this.brain.phase === "hidden") presence.arrive();
    const key = JSON.stringify(raw.focus);
    if (key === this.#lastFocus || presence.world === null) return;
    this.#lastFocus = key;
    const now = performance.now() / 1000;
    this.mind.feel("focus", now);
    if (this.scout.focus(presence.world.focus)) {
      // Первый раз за день в программе или мечется — фраза для ближайшего «поговорить» (BEHAVIOR §4.4).
      this.conductor.topicLine = this.life.focus(this.scout.topic, now) ?? this.conductor.topicLine;
    }
  }

  onMain(state: MainState): void {
    this.presence.setMain(state);
    this.refresh();
  }

  onHost(id: number, rect: Rect | null): void {
    if (this.presence.world === null) return;
    const css = rect === null ? null : this.presence.toCss(rect);
    this.brain.hostMoved(id, css);
    if (id === this.#attached) this.reactions.host(css, performance.now() / 1000);
  }

  onCursor(x: number, y: number): void {
    this.brain.cursorX = x;
    this.#cursor = { x, y };
    this.#cursorFedAt = performance.now();
    this.#movedAt = this.#cursorFedAt;
    this.reactions.cursor(x, y, this.#cursorFedAt / 1000, this.presence.shown);
    this.#playWith(x, y, this.#cursorFedAt);
  }

  /** Игра с курсором (этап 4): кружат рядом — стимул «Разуму»; курсор у груди во время игры — «Поймал!». */
  #playWith(x: number, y: number, now: number): void {
    const brain = this.brain;
    const chest =
      this.presence.shown && brain.phase !== "hidden"
        ? { x: brain.x, y: brain.y - brain.chest }
        : null;
    if (this.#play.feed(x, y, now, chest)) this.mind.feel("play", now / 1000, 1, 6);
    const playing = this.mind.activity === "play" || now - this.#caughtAt < 8000;
    if (chest === null || !playing || !caught(x, y, chest) || now - this.#caughtAt < 3000) return;
    this.#caughtAt = now;
    this.speak(pickOne(locale.t.companion.triggers.caught), "direct");
    brain.emote("dance", 1.2);
  }

  onFeed(feed: Feed): void {
    if (isLang(feed.lang) && locale.lang !== feed.lang) locale.set(feed.lang);
    const look = this.look;
    look.mouth = feed.mouth;
    look.speaking = feed.speaking;
    this.#assistant = feed.speaking;
    this.#onRadio(feed.radio ?? null, feed.speaking);
    look.hue =
      new Map<string, number>(Object.entries(EMOTION_HUE)).get(feed.emotion) ?? EMOTION_HUE.neutral;
    this.#feel(feed.emotion);
    if (!feed.speaking) return;
    this.brain.wake();
    // Новый ответ ассистента — с ним говорят, радость чуть растёт (BEHAVIOR §2).
    if (this.speech.reply(feed.text, performance.now())) this.life.event("talk");
  }

  /** Вышел из портала — поздоровался (T6): по привязанности тепло или сдержанно, иначе обычно. */
  #greet(): void {
    const special = this.life.greeting();
    if (special === null) {
      this.reactions.greet(performance.now() / 1000);
      return;
    }
    this.speak(special, "reaction");
    this.brain.emote("wave", 2);
  }

  /** Эмоция ответа ассистента сменилась — показать её телом коротко (COMPANION.md, этап 2). */
  #feel(emotion: string): void {
    if (emotion === this.#emotion) return;
    this.#emotion = emotion;
    const pose = EMOTION_POSE.get(emotion);
    if (pose !== undefined && !this.brain.watching) this.brain.emote(pose[0], pose[1]);
  }

  /** Зов «Умник», пока спутник на экране: облачко вместо окна. */
  onCalled(): void {
    this.speech.call(performance.now());
    this.look.attention = 1;
    this.brain.wake();
  }

  /** Погладили: сердечки, прыжок радости, фраза; на значке — значок любимее (BEHAVIOR §6–§7). */
  pet(now: number): void {
    const brain = this.brain;
    brain.pet();
    this.look.attention = Math.max(this.look.attention, 0.5);
    this.reactions.pet(now / 1000);
    const spot = brain.spot;
    if (spot?.surface.kind !== "edge" || spot.surface.host !== ICONS) return;
    const under = this.scout.icons.find(
      (one) => brain.x >= one.rect.x - 10 && brain.x <= one.rect.x + one.rect.w + 10,
    );
    if (under !== undefined) this.life.petOn(under.name);
  }

  /** Сколько кадров в секунду нужно сейчас: 60 в движении и с эффектами, 20 в покое, 8 во сне. */
  fps(): number {
    const body = this.brain.body();
    const still = this.brain.phase === "rest" && body.effects.length === 0 && !this.gestures.active;
    const smoothing = this.stage?.animating ?? false;
    if (!still || smoothing || this.look.speaking || this.look.attention > 0.01) return 60;
    return body.pose === "sleep" ? 8 : 20;
  }

  /** Один кадр: решение, тело, реакции, голос, отрисовка, область кликов. */
  frame(dt: number, now: number, view: { menuOpen: boolean; card: Rect | null }): void {
    this.#think(now);
    const brain = this.brain;
    brain.busy = this.conductor.poking || this.speech.own(now);
    this.gestures.tick(now);
    brain.tick(dt);
    this.reactions.tick(now / 1000);
    if (brain.phase === "climb" && this.#lastPhase !== "climb") this.reactions.climbing();
    this.#lastPhase = brain.phase;
    this.#feedCursor(now);
    this.look.attention = Math.max(0, this.look.attention - dt * 0.8);
    const body = brain.body();
    body.effects = [...body.effects, ...this.gestures.effects()];
    this.stage?.draw(body, this.look, dt);
    this.presence.tick();
    this.#sendHit(view);
    this.#syncHost();
  }

  #think(now: number): void {
    this.conductor.update(now, {
      listening: this.#assistant || this.speech.listening,
      holding: this.gestures.active,
      behavior: this.settings.behavior,
      calm: this.settings.calm || this.sanity.calm(now / 1000),
      userBusy: now - this.#movedAt < BUSY_MS,
      lastLine: this.speech.last,
    });
    this.scout.pollMedia(now, (change) => {
      if (!this.brain.watching || change === null) return;
      const lines = watchPhrases(locale.lang);
      this.speak(pickOne(change === "paused" ? lines.pause : lines.resume), "reaction", true);
    });
    const long = this.life.tick(now / 1000);
    if (long !== null) this.speak(long, "ambient");
    const line = this.mind.voice.next(now / 1000, {
      blocked:
        !this.presence.shown || this.#assistant || this.speech.listening || this.gestures.active,
      bubble: this.speech.visible(now),
    });
    if (line !== null) {
      this.speech.say(line, now);
      this.sanity.noteLine(now / 1000);
    }
    this.#guard(now);
  }

  /** Сторож раз в секунду: нарушено правило — чинит и пишет в консоль. */
  #guard(now: number): void {
    const brain = this.brain;
    const screen = this.presence.world?.monitor ?? { x: 0, y: 0, w: innerWidth, h: innerHeight };
    const fixes = this.sanity.observe(
      {
        phase: brain.phase,
        x: brain.x,
        y: brain.y,
        screen,
        shown: this.presence.shown,
        holding: this.gestures.active,
        activity: this.mind.activity,
      },
      now / 1000,
    );
    this.mind.voice.hushed = this.sanity.hushed(now / 1000);
    for (const fix of fixes) this.#repair(fix);
  }

  #repair(fix: Fix): void {
    console.warn(
      "[companion] sanity",
      fix,
      this.brain.phase,
      Math.round(this.brain.x),
      Math.round(this.brain.y),
    );
    if (fix === "land") this.brain.rescue();
    else if (fix === "release") this.brain.toss(0, 0);
    else if (fix === "arrive") this.presence.arrive();
    else if (fix === "hide") this.brain.hide();
  }

  /** Курсор стоит — событий нет, а «что смотришь?» (T8) ждёт 4 с: подкармливаем 4 раза в секунду. */
  #feedCursor(now: number): void {
    const cursor = this.#cursor;
    if (cursor === null || now - this.#cursorFedAt <= CURSOR_FEED_MS) return;
    this.#cursorFedAt = now;
    this.reactions.cursor(cursor.x, cursor.y, now / 1000, this.presence.shown);
  }

  /** Радио сменило состояние: поёт или слушает; фраза на включение, смену станции, паузу, выключение. */
  #onRadio(next: RadioFeed | null, speaking: boolean): void {
    const before: RadioMode = this.radio?.mode ?? "off";
    const mode: RadioMode = next?.mode ?? "off";
    this.brain.music = mode === "playing" ? "playing" : mode === "off" ? "off" : "paused";
    const lines = locale.t.radio.lines;
    const switched = next !== null && this.radio !== null && next.title !== this.radio.title;
    const list =
      before === "off" && mode !== "off"
        ? lines.start
        : before !== "off" && mode === "off"
          ? lines.stop
          : before === "playing" && mode === "paused"
            ? lines.pause
            : switched
              ? lines.switch
              : null;
    if (list !== null && this.presence.shown) this.speak(pickOne(list), "reaction");
    this.radio = mode === "off" ? null : next;
    this.look.panel = this.radio === null ? null : this.radio.title;
    // Поёт: рот — по громкости потока; «говорит» — значит, выходки не начинаются.
    if (mode === "playing" && next !== null && !speaking) {
      this.look.mouth = next.level;
      this.look.speaking = true;
    }
  }

  #applyBehavior(): void {
    const brain = this.brain;
    const settings = this.settings;
    // Когда гулять, решает «Разум» (MIND §4), а не таймер тела.
    brain.wander = false;
    brain.calm = settings.behavior === "follow";
    brain.chest = settings.height * 0.55;
    brain.figure = settings.height * CANVAS_RATIO;
  }

  /** Область кликов: персонаж и табличка радио; держат мышью или открыто меню — слой ловит всё. */
  #sendHit(view: { menuOpen: boolean; card: Rect | null }): void {
    const box = this.stage?.bounds ?? null;
    const capture = this.gestures.active || view.menuOpen;
    const hit = this.settings.hologram || box === null ? null : union(box, view.card);
    const key = JSON.stringify([
      hit && [Math.round(hit.x), Math.round(hit.y), Math.round(hit.w)],
      capture,
    ]);
    if (key === this.#lastHit) return;
    this.#lastHit = key;
    this.#ports.hit(hit, capture);
  }

  #syncHost(): void {
    const host = hostOf(this.brain.spot);
    if (host === this.#attached) return;
    this.#attached = host;
    this.#ports.attach(host);
  }
}

function union(box: Rect, card: Rect | null): Rect {
  if (card === null) return box;
  const x = Math.min(box.x, card.x);
  const y = Math.min(box.y, card.y);
  return {
    x,
    y,
    w: Math.max(box.x + box.w, card.x + card.w) - x,
    h: Math.max(box.y + box.h, card.y + card.h) - y,
  };
}
