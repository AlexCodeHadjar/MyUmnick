import { EMOTION_HUE } from "../../avatar/orb/palette";
import type { RadioFeed } from "../../radio";
import { Life, Reactions } from "../behavior";
import { Brain } from "../body";
import { CANVAS_RATIO, type CompanionStage, type Look } from "../look";
import { Mind, Sanity, type VoiceKind } from "../mind";
import { DesktopReactions } from "../behavior/desktopEvents";
import { ICONS, type Rect, type World } from "../space";
import { shouldShow, type CompanionSettings } from "../settings";
import { Conductor } from "./conductor";
import { Escort } from "./escort";
import { Gestures } from "./gestures";
import type { Ports } from "./ports";
import { Presence, type MainState } from "./presence";
import { Scout } from "./scout";
import { Speech } from "./speech";
import { CompanionFrame } from "./frame";
import { CursorInput } from "./cursorInput";
import { AssistantFeed, type Feed } from "./assistantFeed";
export type { Feed } from "./assistantFeed";
const GREET_DELAY_MS = 900;
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
  readonly escort: Escort;
  readonly conductor: Conductor;
  settings: CompanionSettings;
  radio: RadioFeed | null = null;
  stage: CompanionStage | null = null;
  readonly cursor = new CursorInput(this);
  readonly feed = new AssistantFeed(this);
  readonly #frame: CompanionFrame;
  #lastFocus = "";
  readonly desktopReactions = new DesktopReactions();
  constructor(ports: Ports, storage: Storage, settings: CompanionSettings) {
    this.#frame = new CompanionFrame(this, ports);
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
    this.escort = new Escort(brain, this.presence);
    const parts = {
      escort: this.escort,
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
    this.#focus(raw);
  }

  #focus(raw: World): void {
    const presence = this.presence;
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
    if (id === this.#frame.attached) this.reactions.host(css, performance.now() / 1000);
  }

  /** Где пользователь печатает (физические пиксели экрана) или `null` — не печатает. */
  onTyping(rect: Rect | null): void {
    this.escort.caret = rect === null ? null : this.presence.toCss(rect);
  }

  onCursor(x: number, y: number): void {
    this.cursor.onCursor(x, y);
  }
  onFeed(feed: Feed): void {
    this.feed.onFeed(feed);
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

  fps(): number {
    return this.#frame.fps();
  }
  frame(
    dt: number,
    now: number,
    view: { menuOpen: boolean; card: Rect | null; direct?: Rect | null },
  ): void {
    this.#frame.frame(dt, now, view);
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
}
