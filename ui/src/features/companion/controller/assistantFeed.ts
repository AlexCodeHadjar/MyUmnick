import { isLang, locale } from "../../../core";
import { EMOTION_HUE } from "../../avatar/orb/palette";
import type { RadioFeed, RadioMode } from "../../radio";
import { type Pose } from "../space";
import type { CompanionController } from "./controller";
import { pickOne } from "./pickOne";
/** Подача главного окна (`companion-feed`, ADR-0045, ADR-0049). */
export interface Feed {
  mouth: number;
  speaking: boolean;
  emotion: string;
  text: string;
  lang: string;
  radio?: RadioFeed;
}
/** Эмоция → короткая поза тела и её длительность (с); кадры уже есть (FRAMES-2). */
const EMOTION_POSE: ReadonlyMap<string, readonly [Pose, number]> = new Map([
  ["happy", ["wave", 1.6]],
  ["embarrassed", ["wave", 1.2]],
  ["sad", ["sit_corner", 3]],
  ["surprised", ["float", 0.8]],
] as const);
export class AssistantFeed {
  constructor(private readonly owner: CompanionController) {}
  speaking = false;
  #emotion = "neutral";
  /** Текст текущего ответа ассистента — для «покажи на экране». */
  #replyText = "";
  onFeed(feed: Feed): void {
    if (isLang(feed.lang) && locale.lang !== feed.lang) locale.set(feed.lang);
    const look = this.owner.look;
    look.mouth = feed.mouth;
    look.speaking = feed.speaking;
    this.speaking = feed.speaking;
    this.#onRadio(feed.radio ?? null, feed.speaking);
    look.hue =
      new Map<string, number>(Object.entries(EMOTION_HUE)).get(feed.emotion) ?? EMOTION_HUE.neutral;
    this.#feel(feed.emotion);
    this.#reply(feed);
  }
  #reply(feed: Feed): void {
    // Ответ договорён — назвал элемент в кавычках? Показать его на экране (этап 5).
    if (!feed.speaking && this.#replyText !== "") {
      void this.owner.conductor.pointAt(this.#replyText);
      this.#replyText = "";
    }
    if (feed.speaking) this.#replyText = feed.text;
    if (!feed.speaking) return;
    this.owner.brain.wake();
    // Новый ответ ассистента — с ним говорят, радость чуть растёт (BEHAVIOR §2).
    if (this.owner.speech.reply(feed.text, performance.now())) this.owner.life.event("talk");
  }
  /** Эмоция ответа ассистента сменилась — показать её телом коротко (COMPANION.md, этап 2). */
  #feel(emotion: string): void {
    if (emotion === this.#emotion) return;
    this.#emotion = emotion;
    const pose = EMOTION_POSE.get(emotion);
    if (pose !== undefined && !this.owner.brain.watching) this.owner.brain.emote(pose[0], pose[1]);
  }

  /** Радио сменило состояние: поёт или слушает; фраза на включение, смену станции, паузу, выключение. */
  #onRadio(next: RadioFeed | null, speaking: boolean): void {
    const mode = radioMode(next);
    this.owner.brain.music = mode === "playing" ? "playing" : mode === "off" ? "off" : "paused";
    const list = radioLine(radioMode(this.owner.radio), mode, this.#switched(next));
    if (list !== null && this.owner.presence.shown) this.owner.speak(pickOne(list), "reaction");
    this.#display(next, mode, speaking);
  }
  #switched(next: RadioFeed | null) {
    return next !== null && this.owner.radio !== null && next.title !== this.owner.radio.title;
  }
  #display(next: RadioFeed | null, mode: RadioMode, speaking: boolean) {
    this.owner.radio = mode === "off" ? null : next;
    this.owner.look.panel = this.owner.radio === null ? null : this.owner.radio.title;
    // Поёт: рот — по громкости потока; «говорит» — значит, выходки не начинаются.
    if (mode === "playing" && next !== null && !speaking) {
      this.owner.look.mouth = next.level;
      this.owner.look.speaking = true;
    }
  }
}

function radioMode(feed: RadioFeed | null): RadioMode {
  return feed?.mode ?? "off";
}
function radioLine(before: RadioMode, mode: RadioMode, switched: boolean) {
  const lines = locale.t.radio.lines;
  if (before === "off" && mode !== "off") return lines.start;
  if (before !== "off" && mode === "off") return lines.stop;
  if (before === "playing" && mode === "paused") return lines.pause;
  return switched ? lines.switch : null;
}
