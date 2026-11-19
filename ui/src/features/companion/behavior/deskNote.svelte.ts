import type { CompanionController } from "../controller";
import { KEEPSAKE_TIMING as timing } from "../settings";
import { locale } from "../../../core";
import { spotOn } from "../space/anchors";
export function createNote(controller: CompanionController, available: () => boolean) {
  let note = $state<{ text: string; x: number; y: number } | null>(null);
  let retrieving = false;
  let nextNote = performance.now() + timing.noteMs;
  function takeNote(): void {
    if (!note || !available()) return;
    const surface = controller.brain.spot?.surface;
    if (surface) controller.brain.goTo(spotOn(surface, note.x, note.y));
    retrieving = true;
  }
  function collect() {
    const brain = controller.brain;
    if (retrieving && note && brain.phase === "rest") {
      note = null;
      retrieving = false;
      brain.emote("note_take", timing.noteS);
    }
  }
  function offer(now: number, x: number, y: number, seconds: number) {
    if (!note && now >= nextNote) {
      nextNote = now + timing.noteMs;
      if (Math.random() < timing.noteChance) {
        const hours = Math.floor(seconds / 3600);
        note = {
          x: Math.max(4, Math.min(innerWidth - 155, x)),
          y: Math.max(4, y - 55),
          text: hours
            ? locale.t.companion.keepsakes.hours.replace("{n}", String(hours))
            : locale.t.companion.keepsakes.water,
        };
        controller.brain.emote("note_put", timing.noteS);
      }
    }
  }
  return {
    takeNote,
    collect,
    offer,
    get note() {
      return note;
    },
  };
}
