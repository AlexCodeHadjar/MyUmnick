import { locale } from "../../../core";
import { type Fix } from "../mind";
import { watchPhrases } from "../phrases";
import { Diversions } from "../behavior/diversions";
import { hostOf, type Rect } from "../space";
import { DIVERSION } from "../settings";
import type { Ports } from "./ports";
import type { CompanionController } from "./controller";
import { pickOne } from "./pickOne";
type Body = ReturnType<CompanionController["brain"]["body"]>;
const BUSY_MS = 60_000;
export class CompanionFrame {
  constructor(
    private readonly owner: CompanionController,
    readonly ports: Ports,
  ) {}
  attached: number | null = null;
  #lastHit = "";
  #lastPhase = "hidden";
  #startledAt = -Infinity;
  readonly #diversions = new Diversions();
  /** Громкое место фильма — вздрогнул (подскок) и «Ого!», не чаще раза в минуту (этап 5). */
  #startle(now: number): void {
    if (now - this.#startledAt < 60_000) return;
    this.#startledAt = now;
    this.owner.brain.emote("float", 0.5);
    this.owner.speak(pickOne(locale.t.companion.triggers.loud), "reaction", true);
  }

  /** Заиграла музыка в плеере: «О, музыка!» и танец, если не смотрит фильм и не на радио. */
  #dance(): void {
    const brain = this.owner.brain;
    if (brain.watching || brain.music !== "off" || brain.phase !== "rest") return;
    this.owner.speak(pickOne(locale.t.companion.triggers.music), "reaction");
    brain.emote("dance", 4);
  }

  /** Сколько кадров в секунду нужно сейчас: 60 в движении и с эффектами, 20 в покое, 8 во сне. */
  fps(): number {
    const body = this.owner.brain.body();
    const still = this.#still(body);
    const smoothing = this.owner.stage?.animating ?? false;
    if (!still || smoothing || this.owner.look.speaking || this.owner.look.attention > 0.01)
      return 60;
    return body.pose === "sleep" ? 8 : 20;
  }

  #still(body: Body) {
    return (
      this.owner.brain.phase === "rest" && body.effects.length === 0 && !this.owner.gestures.active
    );
  }
  /** Один кадр: решение, тело, реакции, голос, отрисовка, область кликов. */
  frame(
    dt: number,
    now: number,
    view: { menuOpen: boolean; card: Rect | null; direct?: Rect | null },
  ): void {
    this.#think(now);
    const brain = this.owner.brain;
    brain.busy = this.owner.conductor.poking || this.owner.speech.own(now);
    this.owner.gestures.tick(now);
    brain.tick(dt);
    this.owner.reactions.tick(now / 1000);
    if (brain.phase === "climb" && this.#lastPhase !== "climb") this.owner.reactions.climbing();
    this.#lastPhase = brain.phase;
    this.owner.cursor.repeat(now);
    this.owner.look.attention = Math.max(0, this.owner.look.attention - dt * 0.8);
    this.#draw(dt, now, view.menuOpen);
    this.owner.presence.tick();
    this.#sendHit(view);
    this.#syncHost();
  }

  #draw(dt: number, now: number, menuOpen: boolean) {
    const brain = this.owner.brain;
    let body = brain.body();
    const surface = brain.spot?.surface;
    const edge = surface?.kind === "edge" && surface.host >= 0;
    const free = this.#idle() && !menuOpen && this.#poseFree(body, edge) && this.#cursorFar(body);
    let scene = this.#diversions.frame(now, body.phase, free, edge);
    if (scene?.kind === "trip" && brain.stopForPose("trip", DIVERSION.tripMs / 1000)) {
      body = brain.body();
      scene = null;
    }
    body.effects = [...body.effects, ...this.owner.gestures.effects()];
    this.#move(body, now);
    this.owner.stage?.draw(body, this.owner.look, dt, scene);
  }
  #move(body: Body, now: number) {
    if (
      body.phase === "rest" &&
      !this.owner.settings.calm &&
      !this.owner.escort.caret &&
      !this.owner.presence.world?.fullscreen
    ) {
      this.owner.desktopReactions.move(body, now, this.owner.settings.height);
    }
  }
  #idle() {
    return (
      this.owner.presence.shown &&
      !this.owner.presence.world?.fullscreen &&
      !this.owner.settings.calm &&
      !this.owner.brain.busy &&
      !this.owner.brain.watching &&
      !this.owner.look.speaking &&
      !this.owner.gestures.active
    );
  }
  #poseFree(body: Body, edge: boolean) {
    return (
      !this.owner.escort.caret &&
      !body.petting &&
      (body.pose === "stand" || body.pose === "walk" || (edge && body.pose === "sit_edge"))
    );
  }
  #cursorFar(body: Body) {
    const cursor = this.owner.cursor.position;
    const brain = this.owner.brain;
    return (
      cursor === null ||
      Math.hypot(cursor.x - body.x, cursor.y - body.y + brain.chest) > brain.figure
    );
  }
  #think(now: number): void {
    this.owner.conductor.update(now, {
      listening: this.owner.feed.speaking || this.owner.speech.listening,
      holding: this.owner.gestures.active,
      behavior: this.owner.settings.behavior,
      calm: this.owner.settings.calm || this.owner.sanity.calm(now / 1000),
      userBusy: now - this.owner.cursor.movedAt < BUSY_MS,
      lastLine: this.owner.speech.last,
    });
    this.owner.scout.pollMedia(now, (change) => {
      if (change === "music") {
        this.#dance();
        return;
      }
      if (change === "loud") {
        this.#startle(now);
        return;
      }
      if (!this.owner.brain.watching || change === null) return;
      const lines = watchPhrases(locale.lang);
      this.owner.speak(pickOne(change === "paused" ? lines.pause : lines.resume), "reaction", true);
    });
    const long = this.owner.life.tick(now / 1000);
    if (long !== null) this.owner.speak(long, "ambient");
    const line = this.owner.mind.voice.next(now / 1000, {
      blocked:
        !this.owner.presence.shown ||
        this.owner.feed.speaking ||
        this.owner.speech.listening ||
        this.owner.gestures.active,
      bubble: this.owner.speech.visible(now),
    });
    if (line !== null) {
      this.owner.speech.say(line, now);
      this.owner.sanity.noteLine(now / 1000);
    }
    this.#guard(now);
  }

  /** Сторож раз в секунду: нарушено правило — чинит и пишет в консоль. */
  #guard(now: number): void {
    const brain = this.owner.brain;
    const screen = this.owner.presence.world?.monitor ?? {
      x: 0,
      y: 0,
      w: innerWidth,
      h: innerHeight,
    };
    const fixes = this.owner.sanity.observe(
      {
        phase: brain.phase,
        x: brain.x,
        y: brain.y,
        screen,
        shown: this.owner.presence.shown,
        holding: this.owner.gestures.active,
        activity: this.owner.mind.activity,
      },
      now / 1000,
    );
    this.owner.mind.voice.hushed = this.owner.sanity.hushed(now / 1000);
    for (const fix of fixes) this.#repair(fix);
  }

  #repair(fix: Fix): void {
    console.warn(
      "[companion] sanity",
      fix,
      this.owner.brain.phase,
      Math.round(this.owner.brain.x),
      Math.round(this.owner.brain.y),
    );
    if (fix === "land") this.owner.brain.rescue();
    else if (fix === "release") this.owner.brain.toss(0, 0);
    else if (fix === "arrive") this.owner.presence.arrive();
    else if (fix === "hide") this.owner.brain.hide();
  }

  /** Область кликов: персонаж и табличка радио; держат мышью или открыто меню — слой ловит всё. */
  #sendHit(view: { menuOpen: boolean; card: Rect | null; direct?: Rect | null }): void {
    const box = this.owner.stage?.bounds;
    const capture = this.owner.gestures.active || view.menuOpen;
    // «Не мешать кликам»: прямоугольник всё равно шлём — по нему оболочка узнаёт двойной щелчок,
    // которым режим выключается (просьба пользователя 2026-11-18: иначе персонажа не вернуть).
    const ghost = this.owner.settings.hologram;
    const hit = view.direct ?? (box == null ? null : union(box, view.card));
    const key = JSON.stringify([
      hit && [Math.round(hit.x), Math.round(hit.y), Math.round(hit.w), Math.round(hit.h)],
      capture,
      ghost,
    ]);
    if (key === this.#lastHit) return;
    this.#lastHit = key;
    this.ports.hit(hit, capture && !ghost, ghost);
  }

  #syncHost(): void {
    const host = hostOf(this.owner.brain.spot);
    if (host === this.attached) return;
    this.attached = host;
    this.ports.attach(host);
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
