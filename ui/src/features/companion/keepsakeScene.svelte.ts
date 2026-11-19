import { invoke } from "@tauri-apps/api/core";
import { locale } from "../../core";
import type { CompanionController } from "./controller";
import { addItem, parsePocket, type Keepsake } from "./behavior/keepsakes";
import { KEEPSAKE_TIMING as timing } from "./settings";
import { createBuilding } from "./behavior/building.svelte";
import { createNote } from "./behavior/deskNote.svelte";
import type { Pose, Rect } from "./space";

/** Финал находки по `ending`: 0 — в карман, 1 — обратно, 2 — в корзину (затем отряхивает руки). */
const ENDINGS: readonly Pose[] = ["pocket", "put_back", "throw"];
/** Карман — у бедра; находка — в руках у груди (кадры `inspect`, FRAMES-6 §5.14). Доли высоты кадра. */
const POCKET_Y = 0.65;
const HANDS_Y = 0.42;

export function createDesk(controller: CompanionController) {
  const pocketKey = "companion.pocket.v1";
  let pocket = $state(parsePocket(localStorage.getItem(pocketKey)));
  let visible = $state(false);
  let item = $state<Keepsake | null>(null),
    ending = $state(0);
  let actor = $state<HTMLDivElement>();
  let noteEl = $state<HTMLButtonElement>();
  let nextFind = performance.now() + timing.findMs;
  const notes = createNote(controller, available);
  const building = createBuilding(controller);
  let finishAt = 0,
    pending = false;
  /** Финал ещё не показан; отряхнуть руки после броска — в этот момент. */
  let endingShown = true,
    recalled = false,
    dustAt = 0;
  /** Вертит находку до финала, финал — последняя секунда (кадры FRAMES-6). */
  function inspect(now: number): void {
    finishAt = now + timing.inspectMs;
    endingShown = false;
    controller.brain.emote("inspect", (timing.inspectMs - timing.endingMs) / 1000);
  }
  function showEnding(now: number): void {
    endingShown = true;
    // Вспомнил вещь из кармана — кладёт её обратно в карман.
    const pose = recalled ? "pocket" : (ENDINGS[ending] ?? "put_back");
    controller.brain.emote(pose, (pose === "throw" ? timing.throwMs : timing.endingMs) / 1000);
    if (pose === "throw") dustAt = now + timing.throwMs;
  }
  function interactiveRect(): Rect | null {
    const p = controller.escort.cursor;
    if (!noteEl || !p) return null;
    const r = noteEl.getBoundingClientRect();
    if (p.x >= r.left && p.x <= r.right && p.y >= r.top && p.y <= r.bottom)
      return { x: r.left, y: r.top, w: r.width, h: r.height };
    return null;
  }
  function available(): boolean {
    return (
      controller.presence.shown &&
      !controller.presence.world?.fullscreen &&
      !controller.escort.caret &&
      controller.brain.music === "off" &&
      !controller.brain.watching &&
      !controller.gestures.active
    );
  }
  async function find(): Promise<void> {
    pending = true;
    try {
      const found = await invoke<Keepsake | null>("companion_recent");
      if (!found || !available() || controller.brain.phase !== "rest") return;
      item = found;
      ending = Math.floor(Math.random() * 3);
      recalled = false;
      inspect(performance.now());
    } catch {
      /* Recent may be disabled by Windows policy. */
    } finally {
      pending = false;
    }
  }
  function tick(now: number): void {
    const brain = controller.brain,
      box = controller.stage?.bounds,
      world = controller.presence.world;
    building.account(now);
    if (dustAt > 0 && now >= dustAt) {
      dustAt = 0;
      controller.brain.emote("dust_hands", timing.dustMs / 1000);
    }
    if (item && !endingShown && now >= finishAt - timing.endingMs) showEnding(now);
    visible = !!box && !!world && available();
    if (!visible || !world || !box) {
      item = null;
      return;
    }
    const x = Math.max(8, Math.min(innerWidth - 108, box.x + box.w * 0.52));
    const y = Math.max(8, Math.min(innerHeight - 58, box.y + box.h * POCKET_Y));
    if (actor) {
      actor.style.transform = "translate(" + String(x) + "px," + String(y) + "px)";
      actor.style.setProperty("--hands", String(box.h * (HANDS_Y - POCKET_Y)) + "px");
    }
    building.place(world);
    notes.collect();
    if (item && now >= finishAt) {
      if (ending === 0) {
        pocket = addItem(pocket, item);
        localStorage.setItem(pocketKey, JSON.stringify(pocket));
      }
      item = null;
    }
    if (controller.settings.calm || brain.phase !== "rest" || item || brain.busy) return;
    if (now >= nextFind && !pending) {
      nextFind = now + timing.findMs;
      if (
        Math.random() < timing.findChance &&
        ["edge", "floor"].includes(brain.spot?.surface.kind ?? "")
      ) {
        if (pocket.length && Math.random() < timing.recallChance) {
          item = pocket[Math.floor(Math.random() * pocket.length)] ?? null;
          ending = 1;
          recalled = true;
          inspect(now);
          controller.speak(locale.t.companion.keepsakes.recall, "reaction");
        } else void find();
      }
    }
    notes.offer(now, x, y, building.day?.seconds ?? 0);
  }
  return {
    interactiveRect,
    resetBuilding: building.resetBuilding,
    tick,
    takeNote: notes.takeNote,
    get visible() {
      return visible;
    },
    get item() {
      return item;
    },
    get ending() {
      return ending;
    },
    get note() {
      return notes.note;
    },
    get buildingVisible() {
      return building.visible;
    },
    get day() {
      return building.day;
    },
    get actor() {
      return actor;
    },
    get house() {
      return building.house;
    },
    get noteEl() {
      return noteEl;
    },
    set actor(val: HTMLDivElement | undefined) {
      actor = val;
    },
    set house(val: HTMLDivElement | undefined) {
      building.house = val;
    },
    set noteEl(val: HTMLButtonElement | undefined) {
      noteEl = val;
    },
  };
}
