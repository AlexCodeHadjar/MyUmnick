import { locale } from "../../../core";
import { CursorTouch } from "../senses/stroking";
import { caught, PlayWatch } from "../senses";
import type { CompanionController } from "./controller";
import { pickOne } from "./pickOne";
const CURSOR_FEED_MS = 250;
export class CursorInput {
  constructor(private readonly owner: CompanionController) {}
  position: { x: number; y: number } | null = null;
  #cursorFedAt = 0;
  movedAt = 0;
  readonly #play = new PlayWatch();
  #caughtAt = -Infinity;
  readonly #touch = new CursorTouch();
  onCursor(x: number, y: number): void {
    this.owner.brain.cursorX = x;
    this.position = { x, y };
    this.owner.escort.cursor = { x, y };
    this.#cursorFedAt = performance.now();
    this.movedAt = this.#cursorFedAt;
    if (this.#canReact()) this.owner.reactions.cursor(x, y, this.#cursorFedAt / 1000, true);
    const reaction = this.#touch.feed(x, y, this.#cursorFedAt, this.#touchBounds());
    if (reaction === "pet") this.owner.pet(this.#cursorFedAt);
    else if (
      reaction === "reach" &&
      !this.owner.settings.calm &&
      this.owner.brain.spot?.surface.kind === "floor"
    ) {
      this.owner.brain.facing = x < this.owner.brain.x ? -1 : 1;
      this.owner.brain.emote("reach", 0.9);
    } else this.#playWith(x, y, this.#cursorFedAt);
  }

  #canReact(): boolean {
    return (
      this.owner.presence.shown &&
      !this.owner.presence.world?.fullscreen &&
      !this.owner.brain.watching
    );
  }
  #touchBounds() {
    const free =
      this.#canReact() &&
      !this.owner.gestures.active &&
      !this.owner.escort.caret &&
      !this.owner.look.speaking &&
      this.owner.brain.phase === "rest";
    return free ? this.#bounds() : null;
  }
  #bounds() {
    return this.owner.stage?.bounds ?? null;
  }
  /** Игра с курсором (этап 4): кружат рядом — стимул «Разуму»; курсор у груди во время игры — «Поймал!». */
  #playWith(x: number, y: number, now: number): void {
    if (!this.#canReact()) return;
    const brain = this.owner.brain;
    const chest = this.#chest();
    if (this.#play.feed(x, y, now, chest)) this.owner.mind.feel("play", now / 1000, 1, 6);
    const playing = this.owner.mind.activity === "play" || now - this.#caughtAt < 8000;
    if (chest === null || !playing || !caught(x, y, chest) || now - this.#caughtAt < 3000) return;
    this.#caughtAt = now;
    this.owner.speak(pickOne(locale.t.companion.triggers.caught), "direct");
    if (!brain.stopForPose("dance", 1.2)) brain.emote("dance", 1.2);
  }
  #chest() {
    const brain = this.owner.brain;
    return this.owner.presence.shown && brain.phase !== "hidden"
      ? { x: brain.x, y: brain.y - brain.chest }
      : null;
  }
  /** Курсор стоит — событий нет, а «что смотришь?» (T8) ждёт 4 с: подкармливаем 4 раза в секунду. */
  repeat(now: number): void {
    const cursor = this.position;
    if (cursor === null || now - this.#cursorFedAt <= CURSOR_FEED_MS) return;
    this.#cursorFedAt = now;
    if (this.#canReact()) this.owner.reactions.cursor(cursor.x, cursor.y, now / 1000, true);
  }
}
